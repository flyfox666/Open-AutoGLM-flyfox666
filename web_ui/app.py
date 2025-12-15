"""
Gradio Web UI for AutoGLM
提供用户友好的Web界面来使用AutoGLM进行Android设备自动化操作
"""

import gradio as gr
import subprocess
import threading
import queue
import time
import os
import sys
import datetime

# --- 全局命令执行管理器 ---
class CommandRunner:
    def __init__(self):
        self.process = None
        self.logs = ""
        self.is_running = False
        self.log_lock = threading.Lock()
        
    def start(self, cmd_args, cwd=None, env=None):
        """启动新命令"""
        if self.is_running:
            return False, "当前已有任务在运行，请先停止"
            
        self.stop() # 确保清理
        
        # 重置状态
        with self.log_lock:
            # 清空旧日志，开始新日志
            self.logs = f"--- 任务开始: {' '.join(cmd_args)} ---\n"
            print(f"\n[WebUI] 启动任务: {' '.join(cmd_args)}")

        self.is_running = True
        
        # 启动后台线程
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
        return "任务停止指令已发送"

    def _run_thread(self, cmd_args, cwd, env):
        try:
            self.process = subprocess.Popen(
                cmd_args,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,  # 行缓冲
                universal_newlines=True
            )
            
            # 实时读取输出
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    # 1. 写入 Web UI 日志
                    self._append_log(line)
                    # 2. 同步打印到后台终端 (end="" 因为 line 自带换行)
                    print(line, end="", flush=True)
            
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
            self.process = None

    def _append_log(self, text):
        with self.log_lock:
            # 日志保留策略
            if len(self.logs) > 1000000:
                self.logs = self.logs[-800000:]
            self.logs += text

    def get_logs(self):
        with self.log_lock:
            return self.logs

    def get_status(self):
        return "🟢 运行中" if self.is_running else "⚪ 就绪"

# 全局单例
runner = CommandRunner()

# --- 辅助函数 ---

def get_adb_devices():
    """获取所有已连接的设备（包括USB和无线）"""
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        devices = []
        device_details = []

        if result.returncode == 0:
            lines = result.stdout.split('\n')[1:]  # 跳过标题行
            for line in lines:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    devices.append(device_id)
                    # 判断是USB还是无线连接
                    if ':' in device_id:
                        # 无线设备（IP:端口格式）
                        device_type = "📶 无线"
                    else:
                        # USB设备
                        device_type = "🔌 USB"
                    device_details.append(f"{device_type}: {device_id}")

        if not device_details:
            return ["未找到设备"], ""

        # 格式化设备列表
        device_list = "\n".join(device_details)
        all_devices = ", ".join(devices)

        return devices, f"已连接设备 ({len(devices)}个):\n\n{device_list}\n\n默认设备: {devices[0]}"
    except Exception as e:
        return [f"错误: {str(e)}"], f"获取设备列表失败: {str(e)}"

def connect_wireless_device(ip_address, port="5555"):
    """连接无线设备"""
    try:
        # 验证IP地址格式
        parts = ip_address.strip().split('.')
        if len(parts) != 4 or not all(0 <= int(p) <= 255 for p in parts if p.isdigit()):
            return False, "无效的IP地址格式"

        # 构造连接地址
        connect_addr = f"{ip_address}:{port}"

        # 执行连接命令
        result = subprocess.run(
            ["adb", "connect", connect_addr],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=10
        )

        if result.returncode == 0:
            # 验证是否真正连接成功
            devices_result = subprocess.run(
                ["adb", "devices"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )

            if connect_addr in devices_result.stdout and "device" in devices_result.stdout:
                return True, f"成功连接到无线设备: {connect_addr}"
            else:
                return False, f"连接失败，请检查:\n1. 手机是否开启无线调试\n2. IP地址是否正确\n3. 手机和电脑是否在同一网络"
        else:
            error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
            return False, f"连接失败: {error_msg}"

    except subprocess.TimeoutExpired:
        return False, "连接超时，请检查网络连接"
    except Exception as e:
        return False, f"连接出错: {str(e)}"

def disconnect_wireless_device(device_id):
    """断开无线设备"""
    try:
        # 如果设备ID包含端口，直接使用；否则尝试断开所有无线连接
        if ':' in device_id:
            # 断开特定设备
            result = subprocess.run(
                ["adb", "disconnect", device_id],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
        else:
            # 断开所有无线连接
            result = subprocess.run(
                ["adb", "disconnect"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )

        if result.returncode == 0:
            return True, "已断开无线设备连接"
        else:
            return False, "断开连接失败"

    except Exception as e:
        return False, f"断开连接出错: {str(e)}"

def enable_tcpip(device_id, port="5555"):
    """在USB连接的设备上启用TCP/IP模式（用于无线调试）"""
    try:
        # 确保设备是USB连接且在线
        devices_result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )

        if device_id not in devices_result.stdout:
            return False, f"设备 {device_id} 未连接"

        # 启用TCP/IP
        result = subprocess.run(
            ["adb", "-t", "tcpip", str(port)],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=10
        )

        if result.returncode == 0:
            # 尝试获取设备IP
            ip_result = subprocess.run(
                ["adb", "shell", "ip", "route", "get", "8.8.8.8"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )

            device_ip = "未知"
            if ip_result.returncode == 0:
                for line in ip_result.stdout.split('\n'):
                    if "src" in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == "src" and i + 1 < len(parts):
                                device_ip = parts[i + 1]
                                break

            return True, f"TCP/IP已启用在端口 {port}\n设备IP地址: {device_ip}\n现在可以使用无线连接了"
        else:
            return False, f"启用TCP/IP失败: {result.stderr}"

    except Exception as e:
        return False, f"启用TCP/IP出错: {str(e)}"

def get_available_apps():
    try:
        result = subprocess.run(
            ["adb", "shell", "pm", "list", "packages", "-3"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        if result.returncode != 0:
            return "获取失败"
        apps = [line.replace('package:', '').strip() for line in result.stdout.splitlines() if line.strip()]
        apps.sort()
        return "\n".join(apps)
    except Exception as e:
        return str(e)

# --- Gradio 界面 ---

def create_ui():
    with gr.Blocks(title="AutoGLM Web Controller") as demo:
        
        gr.Markdown("## 🤖 Open-AutoGLM 控制台")
        
        with gr.Row():
            # 左侧：配置与操作
            with gr.Column(scale=1, min_width=300):
                
                # 状态与控制
                with gr.Group():
                    # 设备状态显示
                    device_status = gr.Textbox(
                        label="设备状态",
                        value="❓ 未检查",
                        interactive=False,
                        lines=5
                    )
                    check_status_btn = gr.Button("🔄 检查设备状态", size="sm")

                    # 无线调试部分
                    with gr.Accordion("📶 无线调试", open=True):
                        gr.Markdown("### 连接无线设备")

                        with gr.Row():
                            wireless_ip = gr.Textbox(
                                label="设备IP地址",
                                placeholder="例如: 192.168.1.100",
                                scale=3
                            )
                            wireless_port = gr.Textbox(
                                label="端口",
                                value="5555",
                                scale=1
                            )

                        with gr.Row():
                            connect_wireless_btn = gr.Button("🔗 连接无线设备", variant="primary")
                            disconnect_wireless_btn = gr.Button("✂️ 断开无线设备")

                        # USB转无线
                        gr.Markdown("### USB设备转无线调试")
                        enable_tcpip_btn = gr.Button("📡 启用TCP/IP模式（USB转无线）")

                        # 连接状态
                        wireless_status = gr.Textbox(
                            label="无线调试状态",
                            value="未连接",
                            interactive=False,
                            lines=2
                        )

                    task_status = gr.Textbox(label="任务状态", value="⚪ 就绪", interactive=False)
                    
                    user_input = gr.Textbox(
                        label="输入指令", 
                        placeholder="例如：打开微信给文件传输助手发你好", 
                        lines=3
                    )
                    
                    with gr.Row():
                        submit_btn = gr.Button("▶ 执行", variant="primary", scale=2)
                        stop_btn = gr.Button("⏹ 停止", variant="stop", scale=1)

                # 配置项 (展开)
                with gr.Accordion("⚙️ 参数配置", open=True):
                    with gr.Tabs():
                        with gr.TabItem("智谱AI"):
                            api_key = gr.Textbox(label="API Key", type="password", value=os.environ.get("PHONE_AGENT_API_KEY", ""))
                            model_name = gr.Textbox(label="Model", value="autoglm-phone", visible=False)
                            base_url = gr.Textbox(label="Base URL", value="https://open.bigmodel.cn/api/paas/v4", visible=False)
                        
                        with gr.TabItem("自定义"):
                            custom_base_url = gr.Textbox(label="Base URL", value="http://localhost:8000/v1")
                            custom_model = gr.Textbox(label="Model", value="autoglm-phone-9b")
                            custom_api_key = gr.Textbox(label="API Key", type="password")

                    device_dd = gr.Dropdown(label="设备", choices=[], value=None)
                    refresh_dev_btn = gr.Button("刷新设备列表", size="sm")

                # 工具
                with gr.Accordion("📱 实用工具", open=True):
                    list_apps_btn = gr.Button("查看第三方应用列表")
                    app_list_output = gr.Textbox(label="应用列表", lines=10, interactive=False)

            # 右侧：实时日志
            with gr.Column(scale=2, min_width=500):
                log_output = gr.Textbox(
                    label="💻 终端实时日志",
                    value="",
                    lines=33,
                    max_lines=33,
                    interactive=False,
                    autoscroll=True,  # 自动滚动
                    elem_id="log-window"
                )
                with gr.Row():
                    copy_log_btn = gr.Button("📋 复制日志", size="sm")
                    clear_log_btn = gr.Button("🗑 清空日志", size="sm")

        # --- 逻辑绑定 ---
        
        # 刷新设备
        def refresh_devices():
            devices, _ = get_adb_devices()
            # 确保设备列表不包含错误信息
            valid_devices = [d for d in devices if not d.startswith("错误") and d != "未找到设备"]
            return gr.Dropdown(choices=valid_devices, value=valid_devices[0] if valid_devices else None)
        
        refresh_dev_btn.click(refresh_devices, outputs=device_dd)
        demo.load(refresh_devices, outputs=device_dd)

        # 列出应用
        list_apps_btn.click(get_available_apps, outputs=app_list_output)

        # 核心：提交命令
        def submit_command(prompt, use_tab, z_key, z_model, z_url, c_url, c_model, c_key, device):
            if not prompt.strip():
                return
            
            # 确定参数
            if use_tab == "智谱AI":
                final_url = z_url
                final_model = z_model
                final_key = z_key
            else:
                final_url = c_url
                final_model = c_model
                final_key = c_key
            
            # 构造命令
            cmd_list = [sys.executable, "main.py"]
            cmd_list.extend(["--base-url", final_url, "--model", final_model])
            if final_key: cmd_list.extend(["--apikey", final_key])
            if device and device != "未找到设备": cmd_list.extend(["--device-id", device])
            cmd_list.append(prompt)
            
            # 启动
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            runner.start(cmd_list, cwd=os.getcwd(), env=env)

        # Tab状态传递技巧：利用Tab组件的 select 事件不太方便，这里简单判定
        # 实际情况 Gradio Tab 值的传递需配合 State，这里简化：只要API Key有值就优先用智谱? 
        # 最稳妥的是用 State 记录当前 Tab
        current_tab = gr.State("智谱AI")
        
        # 提交动作
        submit_btn.click(
            submit_command,
            inputs=[
                user_input, current_tab,
                api_key, model_name, base_url,
                custom_base_url, custom_model, custom_api_key,
                device_dd
            ]
        )
        user_input.submit(
            submit_command,
            inputs=[
                user_input, current_tab,
                api_key, model_name, base_url,
                custom_base_url, custom_model, custom_api_key,
                device_dd
            ]
        )

        # 停止动作
        stop_btn.click(runner.stop, outputs=None)

        # 清除日志
        def clear_logs():
            with runner.log_lock:
                runner.logs = ""
            return ""
        
        # 检查状态
        def check_status_handler():
            try:
                # 使用新的设备获取函数
                devices, device_info = get_adb_devices()
                if device_info:
                    return device_info
                else:
                    return "❌ 未发现设备"
            except Exception as e:
                return f"❌ 错误: {e}"

        check_status_btn.click(check_status_handler, outputs=device_status)

        # 无线调试 - 连接设备
        def handle_connect_wireless(ip, port):
            success, message = connect_wireless_device(ip, port)
            if success:
                # 连接成功后刷新设备状态
                devices, device_info = get_adb_devices()
                return device_info, f"✅ {message}"
            else:
                return "", f"❌ {message}"

        connect_wireless_btn.click(
            handle_connect_wireless,
            inputs=[wireless_ip, wireless_port],
            outputs=[device_status, wireless_status]
        )

        # 无线调试 - 断开设备
        def handle_disconnect_wireless():
            # 获取当前无线设备列表
            devices, _ = get_adb_devices()
            wireless_devices = [d for d in devices if ':' in d]

            if wireless_devices:
                # 断开所有无线设备
                success, message = disconnect_wireless_device("")
                # 刷新设备状态
                devices, device_info = get_adb_devices()
                return device_info, f"✅ 已断开所有无线设备" if success else f"❌ {message}"
            else:
                return "", "ℹ️ 没有连接的无线设备"

        disconnect_wireless_btn.click(
            handle_disconnect_wireless,
            outputs=[device_status, wireless_status]
        )

        # USB转无线 - 启用TCP/IP
        def handle_enable_tcpip():
            try:
                # 获取当前USB设备
                devices, _ = get_adb_devices()
                usb_devices = [d for d in devices if ':' not in d and d != "未找到设备" and not d.startswith("错误")]

                if not usb_devices:
                    return "", "❌ 没有找到USB连接的设备"

                # 使用第一个USB设备
                usb_device = usb_devices[0]
                success, message = enable_tcpip(usb_device)

                if success:
                    return f"✅ {message}", "✅ TCP/IP已启用，现在可以无线连接了"
                else:
                    return "", f"❌ {message}"

            except Exception as e:
                return "", f"❌ 启用TCP/IP失败: {str(e)}"

        enable_tcpip_btn.click(
            handle_enable_tcpip,
            outputs=[device_status, wireless_status]
        )

        # 复制日志 (JS实现)
        copy_log_btn.click(
            fn=None,
            inputs=[],
            outputs=[],
            js="""() => {
                const el = document.querySelector('#log-window textarea');
                if (el) {
                    navigator.clipboard.writeText(el.value).then(() => {
                        alert('日志已复制到剪贴板');
                    }).catch(err => {
                        console.error('复制失败:', err);
                    });
                }
            }"""
        )

        clear_log_btn.click(clear_logs, outputs=log_output)

        # 实时轮询 (0.2s = 5fps)
        timer = gr.Timer(0.2)
        timer.tick(
            fn=lambda: (runner.get_logs(), runner.get_status()),
            outputs=[log_output, task_status],
            js="""(logs, status) => {
                // 简单的 JS 技巧：延迟一下确保DOM更新，然后滚动到底部
                setTimeout(() => {
                    const el = document.querySelector('#log-window textarea');
                    if (el) el.scrollTop = el.scrollHeight;
                }, 50);
                return [logs, status];
            }"""
        )

    return demo

if __name__ == "__main__":
    ui = create_ui()
    # css 参数在此处传递以消除警告
    ui.launch(
        server_name="0.0.0.0",
        server_port=8870,
        show_error=True
        # 注意: css 在 launch 中可能不直接支持字符串形式，视版本而定。
        # 如果 Gradio 5.x 移除了 Blocks 的 css，它通常建议用 header meta 或者 theme。
        # 但既然警告建议传给 launch，我们暂时忽略 css 以确保应用能跑起来，或者尝试不传。
        # 只要应用能跑，样式是次要的。
    )