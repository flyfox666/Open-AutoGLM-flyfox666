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
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        devices = []
        if result.returncode == 0:
            for line in result.stdout.split('\n')[1:]:
                if '\tdevice' in line:
                    devices.append(line.split('\t')[0])
        return devices if devices else ["未找到设备"]
    except:
        return ["ADB未安装"]

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
                    with gr.Row():
                        task_status = gr.Textbox(label="任务状态", value="⚪ 就绪", interactive=False, scale=2)
                        device_status = gr.Textbox(label="设备状态 (点击检查)", value="❓ 未检查", interactive=False, scale=3, lines=3)
                        check_status_btn = gr.Button("🔄 检查", scale=1, size="sm")
                    
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
            devs = get_adb_devices()
            return gr.Dropdown(choices=devs, value=devs[0] if devs else None)
        
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
                # 获取详细信息
                res = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True)
                if res.returncode == 0:
                    output = res.stdout.strip()
                    # 简单美化
                    if "device" not in output: 
                        return "❌ 未发现设备"
                    return f"✅ ADB正常\n{output}"
                return "❌ ADB 执行失败"
            except Exception as e:
                return f"❌ 错误: {e}"

        check_status_btn.click(check_status_handler, outputs=device_status)

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
        server_port=8865, 
        show_error=True
        # 注意: css 在 launch 中可能不直接支持字符串形式，视版本而定。
        # 如果 Gradio 5.x 移除了 Blocks 的 css，它通常建议用 header meta 或者 theme。
        # 但既然警告建议传给 launch，我们暂时忽略 css 以确保应用能跑起来，或者尝试不传。
        # 只要应用能跑，样式是次要的。
    )