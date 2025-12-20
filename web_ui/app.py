"""
Gradio Web UI for AutoGLM
提供用户友好的Web界面来使用AutoGLM进行Android设备自动化操作
集成轨迹可视化功能
"""

import gradio as gr
import subprocess
import threading
import queue
import time
import os
import sys
import datetime
import json
import re
import glob

from PIL import Image
from io import BytesIO
import base64

# 确保能找到项目模块
if "." not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# megfile/jsonlines 不再需要，使用本地文件系统

# --- 轨迹可视化工具函数 ---

def long_side_resize(image, long_side=600):
    """将图片长边限制到指定尺寸"""
    image = image.convert("RGB")
    width, height = image.size
    if max(width, height) > long_side:
        if width >= height:
            new_width = long_side
            new_height = int(height * long_side / width)
        else:
            new_height = long_side
            new_width = int(width * long_side / height)
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    return image

def image_to_base64(image):
    """将PIL图片转换为base64 URL"""
    buffered = BytesIO()
    image.save(buffered, format="JPEG", quality=85)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/jpeg;base64,{img_str}"

def load_session_logs(session_id):
    """加载指定session的日志"""
    if not session_id:
        return []
    
    log_file = f"running_log/server_log/os-copilot-local-eval-logs/traces/{session_id}.jsonl"
    
    if not os.path.exists(log_file):
        return []
    
    try:
        logs = []
        with open(log_file, "r", encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))
        return logs
    except Exception as e:
        print(f"[ERROR] 加载日志失败: {e}")
        return []

def logs_to_chatbot_messages(logs):
    """将日志转换为Gradio Chatbot格式的消息列表 (Gradio 6.x messages格式)"""
    if not logs:
        return []
    
    messages = []
    
    # 第一条是配置信息
    config_log = logs[0]
    task = config_log.get('message', {}).get('task', '未知任务')
    model_name = config_log.get('message', {}).get('model_config', {}).get('model_name', '未知模型')
    
    # Gradio 6.x 使用 {"role": "user"|"assistant", "content": "..."} 格式
    messages.append({"role": "assistant", "content": f"### 📋 任务: {task}\n\n**模型**: {model_name}"})
    
    # 后续是环境-动作对
    env_act_logs = logs[1:]
    for idx, log in enumerate(env_act_logs):
        try:
            env = log.get('message', {}).get('environment', {})
            act = log.get('message', {}).get('action', {})
            
            image_url = env.get('image', '')
            thought = act.get('cot', '')
            action_type = act.get('action_type', '')
            
            # 尝试加载截图
            img_content = None
            if image_url:
                try:
                    # 检查本地文件是否存在
                    if os.path.exists(image_url):
                        with open(image_url, "rb") as f:
                            image = Image.open(f)
                            image = long_side_resize(image, long_side=800)
                            img_content = image_to_base64(image)
                except Exception as e:
                    print(f"[WARNING] 加载图片失败: {e}")
            
            # 用户消息显示步骤编号 + 截图
            if img_content:
                # Gradio 6.x 支持 gr.Image 或 HTML 格式显示图片
                messages.append({"role": "user", "content": f"📱 Step {idx + 1}\n\n![screenshot]({img_content})"})
            else:
                messages.append({"role": "user", "content": f"📱 Step {idx + 1}"})
            
            # 构建动作描述
            action_desc = f"**Step {idx + 1}**\n\n"
            if thought:
                action_desc += f"💭 **思考**: {thought}\n\n"
            action_desc += f"🎯 **动作**: `{action_type}`\n\n"
            
            # 添加动作详情
            action_copy = {k: v for k, v in act.items() if k not in ['cot']}
            action_desc += f"```json\n{json.dumps(action_copy, indent=2, ensure_ascii=False)}\n```"
            
            # 助手回复动作详情
            messages.append({"role": "assistant", "content": action_desc})
            
        except Exception as e:
            print(f"[WARNING] 处理日志条目失败: {e}")
            continue
    
    return messages

def get_available_sessions():
    """获取所有可用的session ID列表"""
    traces_dir = "running_log/server_log/os-copilot-local-eval-logs/traces"
    if not os.path.exists(traces_dir):
        return []
    
    sessions = []
    for f in glob.glob(os.path.join(traces_dir, "*.jsonl")):
        session_id = os.path.basename(f).replace(".jsonl", "")
        # 获取文件修改时间
        mtime = os.path.getmtime(f)
        sessions.append((session_id, mtime))
    
    # 按时间倒序排列（最新的在前）
    sessions.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in sessions[:20]]  # 只返回最近20个

# --- 全局命令执行管理器 ---
class CommandRunner:
    def __init__(self):
        self.process = None
        self.logs = ""
        self.is_running = False
        self.log_lock = threading.Lock()
        self.current_session_id = None  # 追踪当前session ID
        self.waiting_for_input = False  # 是否等待用户输入
        
    def start(self, cmd_args, cwd=None, env=None):
        """启动新命令"""
        if self.is_running:
            return False, "当前已有任务在运行，请先停止"
            
        self.stop()
        
        with self.log_lock:
            self.logs = f"--- 任务开始: {' '.join(cmd_args)} ---\n"
            self.current_session_id = None  # 重置session ID
            print(f"\n[WebUI] 启动任务: {' '.join(cmd_args)}")

        self.is_running = True
        
        thread = threading.Thread(target=self._run_thread, args=(cmd_args, cwd, env), daemon=True)
        thread.start()
        return True, "任务已启动"

    def stop(self):
        """停止当前任务"""
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                time.sleep(0.5)
                if self.process.poll() is None:
                    self.process.kill()
            except Exception as e:
                self._append_log(f"\n[系统] 停止进程失败: {e}\n")
        
        self.is_running = False
        return True, "任务停止指令已发送"

    def _run_thread(self, cmd_args, cwd, env):
        try:
            self.process = subprocess.Popen(
                cmd_args,
                cwd=cwd,
                env=env,
                stdin=subprocess.PIPE,  # 添加stdin支持
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                universal_newlines=True
            )
            
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    self._append_log(line)
                    print(line, end="", flush=True)
                    
                    # 解析 Session ID
                    match = re.search(r'Session ID:\s*([a-f0-9\-]+)', line)
                    if match:
                        with self.log_lock:
                            self.current_session_id = match.group(1)
                        print(f"[WebUI] 捕获到 Session ID: {self.current_session_id}")
                    
                    # 检测是否需要用户输入
                    if 'Please Reply:' in line or '回复一下' in line:
                        with self.log_lock:
                            self.waiting_for_input = True
            
            self.process.wait()
            end_msg = f"\n--- 任务结束 (代码: {self.process.returncode}) ---\n"
            self._append_log(end_msg)
            print(end_msg)
            
        except Exception as e:
            err_msg = f"\n[系统错误] 执行异常: {str(e)}\n"
            self._append_log(err_msg)
            print(err_msg)
        finally:
            self.is_running = False
            self.waiting_for_input = False
            self.process = None

    def send_input(self, text):
        """发送输入到进程的stdin"""
        if self.process and self.process.poll() is None and self.process.stdin:
            try:
                self.process.stdin.write(text + "\n")
                self.process.stdin.flush()
                self._append_log(f"\n[用户回复] {text}\n")
                with self.log_lock:
                    self.waiting_for_input = False
                return True, "已发送回复"
            except Exception as e:
                return False, f"发送失败: {e}"
        return False, "没有正在运行的任务"

    def _append_log(self, text):
        with self.log_lock:
            if len(self.logs) > 500000:
                self.logs = self.logs[-400000:]
            self.logs += text

    def get_logs(self):
        with self.log_lock:
            return self.logs

    def get_status(self):
        if self.waiting_for_input:
            return "🟡 等待输入"
        return "🟢 运行中" if self.is_running else "⚪ 就绪"
    
    def get_current_session_id(self):
        with self.log_lock:
            return self.current_session_id
    
    def is_waiting_for_input(self):
        with self.log_lock:
            return self.waiting_for_input

# 全局单例
runner = CommandRunner()

# --- 辅助函数 ---

def get_adb_devices():
    """获取所有已连接的设备"""
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        devices = []
        device_details = []

        if result.returncode == 0:
            lines = result.stdout.split('\n')[1:]
            for line in lines:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    devices.append(device_id)
                    device_type = "📶 无线" if ':' in device_id else "🔌 USB"
                    device_details.append(f"{device_type}: {device_id}")

        if not device_details:
            return ["未找到设备"], ""

        device_list = "\n".join(device_details)
        return devices, f"已连接设备 ({len(devices)}个):\n\n{device_list}\n\n默认设备: {devices[0]}"
    except Exception as e:
        return [f"错误: {str(e)}"], f"获取设备列表失败: {str(e)}"

def connect_wireless_device(ip_address, port="5555"):
    """连接无线设备"""
    try:
        parts = ip_address.strip().split('.')
        if len(parts) != 4:
            return False, "无效的IP地址格式"

        connect_addr = f"{ip_address}:{port}"
        result = subprocess.run(
            ["adb", "connect", connect_addr],
            capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=10
        )

        if result.returncode == 0:
            devices_result = subprocess.run(["adb", "devices"], capture_output=True, text=True, encoding='utf-8')
            if connect_addr in devices_result.stdout and "device" in devices_result.stdout:
                return True, f"成功连接到无线设备: {connect_addr}"
            else:
                return False, "连接失败，请检查设备设置"
        else:
            return False, f"连接失败: {result.stderr.strip() if result.stderr else result.stdout.strip()}"

    except subprocess.TimeoutExpired:
        return False, "连接超时"
    except Exception as e:
        return False, f"连接出错: {str(e)}"

def disconnect_wireless_device(device_id):
    """断开无线设备"""
    try:
        result = subprocess.run(
            ["adb", "disconnect"] if not device_id else ["adb", "disconnect", device_id],
            capture_output=True, text=True, encoding='utf-8'
        )
        return True, "已断开无线设备连接"
    except Exception as e:
        return False, f"断开连接出错: {str(e)}"

def enable_tcpip(device_id, port="5555"):
    """启用TCP/IP模式"""
    try:
        result = subprocess.run(
            ["adb", "-s", device_id, "tcpip", str(port)],
            capture_output=True, text=True, encoding='utf-8', timeout=10
        )
        if result.returncode == 0:
            ip_result = subprocess.run(
                ["adb", "-s", device_id, "shell", "ip", "route", "get", "8.8.8.8"],
                capture_output=True, text=True, encoding='utf-8'
            )
            device_ip = "未知"
            if ip_result.returncode == 0 and "src" in ip_result.stdout:
                parts = ip_result.stdout.split()
                for i, part in enumerate(parts):
                    if part == "src" and i + 1 < len(parts):
                        device_ip = parts[i + 1]
                        break
            return True, f"TCP/IP已启用\n设备IP: {device_ip}"
        return False, f"启用失败: {result.stderr}"
    except Exception as e:
        return False, f"启用TCP/IP出错: {str(e)}"

def get_available_apps():
    try:
        result = subprocess.run(
            ["adb", "shell", "pm", "list", "packages", "-3"],
            capture_output=True, text=True, encoding='utf-8', errors='ignore'
        )
        if result.returncode != 0:
            return "获取失败"
        apps = [line.replace('package:', '').strip() for line in result.stdout.splitlines() if line.strip()]
        apps.sort()
        return "\n".join(apps)
    except Exception as e:
        return str(e)

def start_scrcpy():
    """启动 scrcpy 屏幕镜像"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(current_dir)
        scrcpy_path = os.path.join(project_dir, "scrcpy-win64-v3.3.3", "scrcpy.exe")

        if not os.path.exists(scrcpy_path):
            return f"未找到 scrcpy.exe: {scrcpy_path}"

        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, encoding='utf-8')
        devices = [line.split('\t')[0] for line in result.stdout.split('\n')[1:] if '\tdevice' in line]

        if not devices:
            return "没有检测到已连接的设备"

        scrcpy_cmd = [scrcpy_path]
        if len(devices) > 1:
            scrcpy_cmd.extend(['-s', devices[0]])

        def run_scrcpy():
            try:
                if os.name == 'nt':
                    subprocess.Popen(scrcpy_cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
                else:
                    subprocess.Popen(scrcpy_cmd)
            except Exception as e:
                print(f"[ERROR] 启动 scrcpy 失败: {e}")

        threading.Thread(target=run_scrcpy, daemon=True).start()
        time.sleep(0.5)
        return f"✅ scrcpy 已启动 (设备: {devices[0]})"

    except Exception as e:
        return f"启动失败: {str(e)}"

def check_adb_connection():
    """检查ADB连接状态"""
    try:
        subprocess.run(["adb", "start-server"], capture_output=True, text=True, timeout=5)
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            devices = []
            for line in lines[1:]:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        devices.append(f"📱 {parts[0]} - {parts[1]}")

            if devices:
                return True, f"✅ ADB服务正常\n已连接设备:\n" + "\n".join(devices)
            else:
                return False, "⚠️ ADB服务正常但无设备连接"
        return False, f"❌ ADB命令执行失败"

    except FileNotFoundError:
        return False, "❌ ADB未安装或未添加到PATH"
    except subprocess.TimeoutExpired:
        return False, "❌ ADB命令超时"
    except Exception as e:
        return False, f"❌ 检查ADB连接时出错: {str(e)}"

def restart_adb():
    """重启ADB服务"""
    try:
        subprocess.run(["adb", "kill-server"], capture_output=True, text=True, timeout=10)
        time.sleep(1)
        subprocess.run(["adb", "start-server"], capture_output=True, text=True, timeout=10)
        
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            devices = [f"📱 {line.split()[0]}" for line in lines[1:] if '\tdevice' in line]
            if devices:
                return True, f"✅ ADB重启成功\n当前设备:\n" + "\n".join(devices)
            return True, "✅ ADB重启成功\n当前无设备连接"
        return False, "❌ ADB重启失败"
    except Exception as e:
        return False, f"❌ 重启出错: {str(e)}"

# --- Gradio 界面 ---

def create_ui():
    # 自定义CSS：简洁样式
    custom_css = """
    /* 轨迹图片样式 */
    .trajectory-chatbot img {
        max-width: 280px !important;
        max-height: 500px !important;
        width: auto !important;
        height: auto !important;
        object-fit: contain !important;
        cursor: pointer;
        transition: opacity 0.2s;
        border-radius: 8px;
    }
    .trajectory-chatbot img:hover {
        opacity: 0.85;
    }
    .trajectory-chatbot .message {
        max-width: 100% !important;
    }
    """
    
    # 灯箱脚本 - 使用head参数注入 (使用MutationObserver确保动态内容可点击)
    lightbox_head = """
    <style>
    #autoglm-lightbox {
        display: none;
        position: fixed;
        z-index: 999999;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.92);
        justify-content: center;
        align-items: center;
        flex-direction: column;
        cursor: zoom-out;
    }
    #autoglm-lightbox.visible {
        display: flex !important;
    }
    #autoglm-lightbox-img {
        max-width: 95%;
        max-height: 82%;
        object-fit: contain;
        border: 3px solid #fff;
        border-radius: 10px;
        box-shadow: 0 5px 40px rgba(0,0,0,0.6);
    }
    #autoglm-lightbox-controls {
        margin-top: 25px;
        display: flex;
        gap: 20px;
    }
    #autoglm-lightbox-controls button {
        padding: 12px 28px;
        font-size: 15px;
        border: none;
        border-radius: 25px;
        cursor: pointer;
        font-weight: 600;
        transition: all 0.15s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    #autoglm-lightbox-controls button:hover { transform: scale(1.05); }
    #autoglm-lightbox-controls button:active { transform: scale(0.98); }
    #autoglm-lb-download { background: linear-gradient(135deg, #4CAF50, #2E7D32); color: white; }
    #autoglm-lb-close { background: linear-gradient(135deg, #f44336, #c62828); color: white; }
    
    /* 轨迹图片可点击提示 */
    .trajectory-chatbot img,
    [class*="chatbot"] img {
        cursor: zoom-in !important;
        transition: opacity 0.15s ease;
    }
    .trajectory-chatbot img:hover,
    [class*="chatbot"] img:hover {
        opacity: 0.85;
    }
    </style>
    <script>
    (function() {
        'use strict';
        console.log('[AutoGLM] Lightbox v2 loading...');
        
        var lightboxEl = null;
        var lightboxImg = null;
        
        function createLightbox() {
            if (document.getElementById('autoglm-lightbox')) {
                lightboxEl = document.getElementById('autoglm-lightbox');
                lightboxImg = document.getElementById('autoglm-lightbox-img');
                return;
            }
            
            lightboxEl = document.createElement('div');
            lightboxEl.id = 'autoglm-lightbox';
            lightboxEl.innerHTML = '<img id="autoglm-lightbox-img" src="" alt=""><div id="autoglm-lightbox-controls"><button id="autoglm-lb-download">📥 下载图片</button><button id="autoglm-lb-close">✕ 关闭</button></div>';
            document.body.appendChild(lightboxEl);
            
            lightboxImg = document.getElementById('autoglm-lightbox-img');
            
            // 关闭逻辑
            lightboxEl.addEventListener('click', function(e) {
                if (e.target === lightboxEl || e.target.id === 'autoglm-lb-close') {
                    lightboxEl.classList.remove('visible');
                }
            });
            
            // ESC键关闭
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape' && lightboxEl.classList.contains('visible')) {
                    lightboxEl.classList.remove('visible');
                }
            });
            
            // 下载逻辑
            document.getElementById('autoglm-lb-download').addEventListener('click', function(e) {
                e.stopPropagation();
                if (!lightboxImg.src || lightboxImg.src === window.location.href) return;
                
                var a = document.createElement('a');
                a.href = lightboxImg.src;
                a.download = 'autoglm_' + new Date().getTime() + '.png';
                a.style.display = 'none';
                document.body.appendChild(a);
                a.click();
                setTimeout(function() { document.body.removeChild(a); }, 100);
            });
            
            console.log('[AutoGLM] Lightbox created successfully');
        }
        
        function openLightbox(imgSrc) {
            createLightbox();
            lightboxImg.src = imgSrc;
            lightboxEl.classList.add('visible');
            console.log('[AutoGLM] Lightbox opened:', imgSrc.substring(0, 60));
        }
        
        function isChatbotImage(el) {
            if (!el || el.tagName !== 'IMG') return false;
            // 检查多种可能的父容器类名
            var parent = el.closest('.trajectory-chatbot') || 
                         el.closest('[class*="chatbot"]') ||
                         el.closest('.message') ||
                         el.closest('[data-testid="bot"]') ||
                         el.closest('[data-testid="user"]');
            return !!parent;
        }
        
        // 核心：使用捕获阶段拦截所有图片点击
        document.addEventListener('click', function(e) {
            var target = e.target;
            
            // 如果点击的是图片且在Chatbot中
            if (isChatbotImage(target)) {
                e.preventDefault();
                e.stopPropagation();
                openLightbox(target.src);
            }
        }, true); // capture phase
        
        // 初始化
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', createLightbox);
        } else {
            createLightbox();
        }
        
        console.log('[AutoGLM] Lightbox v2 event listeners attached');
    })();
    </script>
    """
    
    with gr.Blocks(title="Open-AutoGLM") as demo:

        gr.Markdown("## 🤖 Open-AutoGLM 控制台")

        with gr.Row():
            # --- 左列：设备管理、配置、任务监控 ---
            with gr.Column(scale=1, min_width=350):
                
                # 1. 设备管理
                with gr.Group():
                    gr.Markdown("### 📱 设备管理")
                    
                    device_status = gr.Textbox(
                        label="设备状态",
                        value="❓ 未检查",
                        interactive=False,
                        lines=3
                    )
                    with gr.Row():
                        check_status_btn = gr.Button("检查", size="sm", min_width=1, scale=1)
                        adb_devices_btn = gr.Button("列表", size="sm", min_width=1, scale=1)
                        restart_adb_btn = gr.Button("重启ADB", size="sm", min_width=1, scale=1)

                    with gr.Accordion("📶 无线调试", open=False):
                        with gr.Row():
                            wireless_ip = gr.Textbox(label="IP", placeholder="192.168.1.x", scale=3)
                            wireless_port = gr.Textbox(label="端口", value="5555", scale=1)
                        
                        with gr.Row():
                            connect_wireless_btn = gr.Button("🔗 连接", variant="primary", size="sm")
                            disconnect_wireless_btn = gr.Button("✂️ 断开", size="sm")

                        enable_tcpip_btn = gr.Button("📡 启用TCP/IP模式", size="sm")
                        wireless_status = gr.Textbox(label="状态", interactive=False, lines=1)

                # 2. 任务监控（放在设备管理下面）
                with gr.Group():
                    gr.Markdown("### 📊 任务监控")
                    with gr.Row():
                        session_dropdown = gr.Dropdown(
                            label="Session",
                            choices=[],
                            value=None,
                            scale=20,
                            allow_custom_value=True,
                            min_width=200
                        )
                        with gr.Column(scale=1, min_width=60):
                            gr.HTML("<div style='height: 26px;'></div>") # 占位符对其下拉框
                            refresh_sessions_btn = gr.Button("🔄", size="sm")
                    
                    task_status = gr.Textbox(
                        label="任务状态",
                        value="⚪ 就绪",
                        interactive=False,
                        lines=1
                    )
                    user_input = gr.Textbox(
                        label="命令/回复",
                        placeholder="输入任务指令 或 回复Agent询问...",
                        lines=2
                    )
                    with gr.Row():
                        submit_btn = gr.Button("▶ 执行/回复", variant="primary", scale=2)
                        stop_btn = gr.Button("⏹ 停止", variant="stop", scale=1)

                # 3. 参数配置 (保留原有的智谱AI/自定义配置)
                with gr.Accordion("⚙️ 参数配置", open=False):
                    with gr.Tabs() as config_tabs:
                        with gr.TabItem("智谱AI"):
                            api_key = gr.Textbox(label="API Key", type="password", value=os.environ.get("PHONE_AGENT_API_KEY", ""))
                            model_name = gr.Textbox(label="Model", value="autoglm-phone", visible=False)
                            base_url = gr.Textbox(label="Base URL", value="https://open.bigmodel.cn/api/paas/v4", visible=False)

                        with gr.TabItem("自定义"):
                            custom_base_url = gr.Textbox(label="Base URL", value="http://localhost:8000/v1")
                            custom_model = gr.Textbox(label="Model", value="autoglm-phone-9b")
                            custom_api_key = gr.Textbox(label="API Key", type="password")

                    with gr.Row():
                        device_dd = gr.Dropdown(label="当前设备", choices=[], value=None, scale=3)
                        refresh_dev_btn = gr.Button("🔄", scale=1)

                # 4. 实用工具
                with gr.Accordion("🛠 实用工具", open=False):
                    scrcpy_btn = gr.Button("🖥️ 启动屏幕镜像", variant="secondary")
                    scrcpy_status = gr.Textbox(label="状态", interactive=False, lines=1)
                    
                    list_apps_btn = gr.Button("📲 获取应用列表", size="sm")
                    app_list_output = gr.Textbox(label="应用列表", lines=3, interactive=False)

            # --- 右列：日志与轨迹并排（更大空间） ---
            with gr.Column(scale=3, min_width=700):
                with gr.Row():
                    # 左边：实时日志
                    with gr.Column(scale=1):
                        gr.Markdown("### 📋 实时日志")
                        log_output = gr.Textbox(
                            label="终端输出",
                            value="",
                            lines=25,
                            max_lines=30,
                            interactive=False,
                            elem_id="log-window"
                        )
                        with gr.Row():
                            clear_log_btn = gr.Button("🗑 清空", size="sm")
                            copy_log_btn = gr.Button("📋 复制", size="sm")
                    
                    # 右边：任务轨迹
                    with gr.Column(scale=1):
                        gr.Markdown("### 📱 任务轨迹")
                        trajectory_output = gr.Chatbot(
                            label="轨迹回放",
                            height=700,
                            show_label=False,
                            elem_classes=["trajectory-chatbot"]
                        )

        # --- 逻辑绑定 ---
        
        # 刷新设备
        def refresh_devices():
            devices, _ = get_adb_devices()
            valid_devices = [d for d in devices if not d.startswith("错误") and d != "未找到设备"]
            return gr.Dropdown(choices=valid_devices, value=valid_devices[0] if valid_devices else None)
        
        refresh_dev_btn.click(refresh_devices, outputs=device_dd)
        demo.load(refresh_devices, outputs=device_dd)

        # 刷新session列表
        def refresh_sessions():
            sessions = get_available_sessions()
            current = runner.get_current_session_id()
            # 如果有当前session且不在列表中，添加到最前面
            if current and current not in sessions:
                sessions = [current] + sessions
            return gr.Dropdown(choices=sessions, value=current if current else (sessions[0] if sessions else None))
        
        refresh_sessions_btn.click(refresh_sessions, outputs=session_dropdown)
        demo.load(refresh_sessions, outputs=session_dropdown)

        # 加载轨迹
        def load_trajectory(session_id):
            if not session_id:
                return []
            logs = load_session_logs(session_id)
            messages = logs_to_chatbot_messages(logs)
            return messages
        
        session_dropdown.change(load_trajectory, inputs=[session_dropdown], outputs=[trajectory_output])

        # 列出应用
        list_apps_btn.click(get_available_apps, outputs=app_list_output)

        # 启动 scrcpy
        scrcpy_btn.click(fn=start_scrcpy, outputs=[scrcpy_status])

        # 核心：智能提交（命令 或 回复）
        def smart_submit(prompt, z_key, z_model, z_url, c_url, c_model, c_key, device):
            if not prompt.strip():
                return runner.get_status(), ""
            
            # 如果任务正在运行且等待输入，作为回复发送
            if runner.is_running and runner.is_waiting_for_input():
                success, msg = runner.send_input(prompt.strip())
                return runner.get_status(), ""  # 清空输入框
            
            # 否则作为新任务启动
            if runner.is_running:
                return "⚠️ 任务运行中，请先停止", prompt
            
            # 判断应该使用哪个API配置
            if z_key and z_key.strip():
                final_url = z_url
                final_model = z_model
                final_key = z_key
                print(f"[WebUI] 使用智谱AI配置: {final_url}")
            else:
                final_url = c_url
                final_model = c_model
                final_key = c_key
                print(f"[WebUI] 使用自定义配置: {final_url}")

            # 构造命令
            cmd_list = [sys.executable, "main.py"]
            cmd_list.extend(["--base-url", final_url, "--model", final_model])
            if final_key: cmd_list.extend(["--apikey", final_key])
            if device and device != "未找到设备": cmd_list.extend(["--device-id", device])
            cmd_list.append(prompt)

            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUNBUFFERED"] = "1"
            
            success, msg = runner.start(cmd_list, cwd=os.getcwd(), env=env)
            return ("🟢 运行中" if success else f"🔴 {msg}"), ""  # 清空输入框

        submit_btn.click(
            smart_submit,
            inputs=[user_input, api_key, model_name, base_url, custom_base_url, custom_model, custom_api_key, device_dd],
            outputs=[task_status, user_input]
        )
        
        user_input.submit(
            smart_submit,
            inputs=[user_input, api_key, model_name, base_url, custom_base_url, custom_model, custom_api_key, device_dd],
            outputs=[task_status, user_input]
        )

        # 停止任务
        def stop_command():
            runner.stop()
            return "⚪ 已停止"
        
        stop_btn.click(stop_command, outputs=[task_status])

        # 检查状态
        def check_status_handler():
            devices, device_info = get_adb_devices()
            return device_info if device_info else "❌ 未发现设备"

        check_status_btn.click(check_status_handler, outputs=device_status)

        # 无线调试
        def handle_connect_wireless(ip, port):
            success, message = connect_wireless_device(ip, port)
            if success:
                devices, device_info = get_adb_devices()
                return device_info, f"✅ {message}"
            return "", f"❌ {message}"

        connect_wireless_btn.click(handle_connect_wireless, inputs=[wireless_ip, wireless_port], outputs=[device_status, wireless_status])

        def handle_disconnect_wireless():
            devices, _ = get_adb_devices()
            wireless_devices = [d for d in devices if ':' in d]
            if wireless_devices:
                disconnect_wireless_device("")
                devices, device_info = get_adb_devices()
                return device_info, "✅ 已断开"
            return "", "ℹ️ 没有无线设备"

        disconnect_wireless_btn.click(handle_disconnect_wireless, outputs=[device_status, wireless_status])

        def handle_enable_tcpip():
            devices, _ = get_adb_devices()
            usb_devices = [d for d in devices if ':' not in d and d != "未找到设备" and not d.startswith("错误")]
            if not usb_devices:
                return "", "❌ 没有USB设备"
            success, message = enable_tcpip(usb_devices[0])
            return (f"✅ {message}", "✅ TCP/IP已启用") if success else ("", f"❌ {message}")

        enable_tcpip_btn.click(handle_enable_tcpip, outputs=[device_status, wireless_status])

        def handle_adb_devices():
            success, message = check_adb_connection()
            return message, message

        adb_devices_btn.click(handle_adb_devices, outputs=[device_status, wireless_status])

        def handle_restart_adb():
            success, message = restart_adb()
            return message, message

        restart_adb_btn.click(handle_restart_adb, outputs=[device_status, wireless_status])

        # 清除日志
        def clear_logs():
            with runner.log_lock:
                runner.logs = ""
            return ""

        clear_log_btn.click(clear_logs, outputs=log_output)

        # 复制日志
        copy_log_btn.click(
            fn=None, inputs=[], outputs=[],
            js="""() => {
                let el = document.querySelector('#log-window textarea');
                if (el && el.value) {
                    navigator.clipboard.writeText(el.value).then(() => alert('已复制')).catch(() => alert('复制失败'));
                }
            }"""
        )

        # 实时轮询
        timer = gr.Timer(1.0)  # 1秒刷新一次
        
        # 保存当前选中的session用于自动刷新轨迹
        current_selected_session = gr.State(value=None)
        # 保存上一次检测到的运行中session，用于判断是否启动了新任务
        last_detected_session = gr.State(value=None)
        
        def poll_updates(selected_session, last_session):
            logs = runner.get_logs()
            status = runner.get_status()
            current_session = runner.get_current_session_id()
            
            # 获取可用sessions
            sessions = get_available_sessions()
            if current_session and current_session not in sessions:
                sessions = [current_session] + sessions
            
            # 判断是否启动了新任务（current_session 发生变化且不为空）
            new_task_started = (current_session and current_session != last_session)
            
            # 确定要显示的session：
            # 1. 如果启动了新任务，自动切换到新的session
            # 2. 否则，如果用户已手动选择了session，保持用户选择
            # 3. 只有当用户未选择时(None)，才使用当前运行的session
            if new_task_started:
                display_session = current_session
                new_selected = current_session  # 更新用户选择为新session
            elif selected_session:
                display_session = selected_session
                new_selected = selected_session
            else:
                display_session = current_session
                new_selected = current_session
            
            # 自动加载轨迹
            trajectory_messages = []
            if display_session:
                traj_logs = load_session_logs(display_session)
                trajectory_messages = logs_to_chatbot_messages(traj_logs)
            
            # 更新 last_detected_session 为当前检测到的session
            new_last_session = current_session if current_session else last_session
            
            return (
                logs, 
                status, 
                gr.Dropdown(choices=sessions, value=display_session),
                trajectory_messages,
                new_selected,
                new_last_session
            )
        
        timer.tick(
            fn=poll_updates,
            inputs=[current_selected_session, last_detected_session],
            outputs=[log_output, task_status, session_dropdown, trajectory_output, current_selected_session, last_detected_session],
            js="""() => {
                setTimeout(() => {
                    // 日志窗口自动滚动
                    let logEl = document.querySelector('#log-window textarea');
                    if (logEl) { logEl.scrollTop = logEl.scrollHeight; }
                    // 轨迹窗口自动滚动
                    let trajEl = document.querySelector('.trajectory-chatbot');
                    if (trajEl) {
                        let scrollContainer = trajEl.querySelector('[class*="chatbot"]') || trajEl;
                        scrollContainer.scrollTop = scrollContainer.scrollHeight;
                    }
                }, 100);
            }"""
        )
        
        # 当用户手动选择session时更新state
        def on_session_select(session_id):
            messages = load_trajectory(session_id)
            return messages, session_id
        
        session_dropdown.change(
            on_session_select,
            inputs=[session_dropdown],
            outputs=[trajectory_output, current_selected_session]
        )

    return demo, custom_css, lightbox_head

if __name__ == "__main__":
    ui, css, head = create_ui()
    ui.launch(
        server_name="0.0.0.0",
        server_port=8870,
        show_error=True,
        css=css,
        head=head
    )