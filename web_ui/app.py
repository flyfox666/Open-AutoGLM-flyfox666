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
import json
from typing import Optional, Tuple, Dict, Any, Generator

# 预设的模型配置
PRESET_CONFIGS = {
    "智谱AI (官方服务)": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "autoglm-phone",
        "description": "智谱AI官方提供的AutoGLM服务，需要API Key"
    }
}

# 检查Gradio版本兼容性
GRADIO_VERSION = gr.__version__.split('.')[0]  # 获取主版本号
SUPPORTS_SHOW_COPY_BUTTON = False

# 尝试检查是否支持show_copy_button
try:
    import inspect
    sig = inspect.signature(gr.Textbox.__init__)
    if 'show_copy_button' in sig.parameters:
        SUPPORTS_SHOW_COPY_BUTTON = True
except:
    pass

class AutoGLMInterface:
    def __init__(self):
        self.process_queue = queue.Queue()
        self.current_process = None
        self.stop_flag = threading.Event()

    def execute_command_stream(self, command: str, base_url: str, model: str,
                             api_key: str = "", device_id: str = "") -> Generator[str, None, None]:
        """执行AutoGLM命令 - 流式输出"""
        try:
            # 获取项目根目录（包含main.py的目录）
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            main_py_path = os.path.join(project_root, "main.py")

            # 构建环境变量
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'

            # 构建命令参数
            cmd = [
                'python', main_py_path,
                '--base-url', base_url,
                '--model', model,
                command
            ]

            if api_key:
                cmd.extend(['--apikey', api_key])
            if device_id:
                cmd.extend(['--device-id', device_id])

            # 设置进度回调
            def progress_callback(progress=0.0, desc="处理中..."):
                pass  # Gradio会自动处理进度

            # 执行命令 - 同时显示终端输出和捕获结果
            self.stop_flag.clear()

            # 创建子进程，允许终端输出显示
            process = subprocess.Popen(
                cmd,
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 将stderr重定向到stdout
                text=True,
                encoding='utf-8',
                errors='ignore',
                env=env,
                universal_newlines=True
            )

            # 实时读取输出并流式返回
            try:
                for line in iter(process.stdout.readline, ''):
                    if line:
                        # 实时打印到终端
                        print(line.rstrip('\n'))

                        # 过滤并流式返回有用的输出
                        line_stripped = line.rstrip('\n')
                        if (line_stripped.strip() and
                            not line_stripped.startswith('[DEBUG]') and
                            not line_stripped.startswith('INFO:')):
                            yield line_stripped

                # 等待进程完成
                process.wait()
                yield "\n执行完成"

            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                yield "执行超时，请检查设备连接或重试"

        except Exception as e:
            yield f"执行出错: {str(e)}"

    def execute_command(self, command: str, base_url: str, model: str,
                       api_key: str = "", device_id: str = "") -> str:
        """执行AutoGLM命令（兼容性方法）"""
        result = ""
        for chunk in self.execute_command_stream(command, base_url, model, api_key, device_id):
            result += chunk + "\n"
        return result

    def get_available_apps(self):
        """获取可用应用列表"""
        try:
            result = subprocess.run(
                ["adb", "shell", "pm", "list", "packages", "-3"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=10
            )

            if result.returncode == 0:
                packages = result.stdout.strip().split('\n')
                app_list = []
                for pkg in packages:
                    if pkg.startswith('package:'):
                        app_name = pkg.replace('package:', '')
                        app_list.append(app_name)

                if app_list:
                    return f"找到 {len(app_list)} 个第三方应用:\n\n" + '\n'.join(sorted(app_list)[:50])
                else:
                    return "未找到第三方应用"
            else:
                return "获取应用列表失败，请检查设备连接"

        except Exception as e:
            return f"获取应用列表出错: {str(e)}"

    def check_device_status(self):
        """检查设备连接状态"""
        try:
            result = subprocess.run(
                ["adb", "devices", "-l"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=10
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                devices = []

                for line in lines[1:]:  # 跳过标题行
                    if line.strip():
                        # 使用正则表达式匹配
                        import re
                        if re.search(r'^[a-zA-Z0-9]+\s+device\b', line):
                            parts = line.split()
                            if len(parts) >= 2:
                                device_id = parts[0]
                                status = parts[1]
                                # 提取设备型号
                                model = "未知型号"
                                for part in parts[2:]:
                                    if part.startswith("model:"):
                                        model = part.split(":", 1)[1]
                                        break
                                devices.append(f"设备ID: {device_id}\n型号: {model}")

                if devices:
                    device_info = f"已检测到 {len(devices)} 个设备\n\n" + "\n\n".join(devices)
                    return "已连接", device_info
                else:
                    return "未连接", "未检测到Android设备"
            else:
                return "检查失败", "ADB命令执行失败"

        except Exception as e:
            return "检查失败", f"检查设备状态时出错: {str(e)}"

def run_autoglm_command_stream(command: str, use_preset: bool, preset_base_url: str, preset_model: str,
                              api_key: str, device_id: str, custom_base_url: str, custom_model: str,
                              custom_api_key: str, custom_device_id: str):
    """运行AutoGLM命令的流式包装函数 - 累积式输出"""
    try:
        autoglm = AutoGLMInterface()

        # 根据选择的类型决定使用哪种配置
        if use_preset:
            base_url = preset_base_url
            model = preset_model
            api_key_to_use = api_key
            device_id_to_use = device_id
        else:
            base_url = custom_base_url
            model = custom_model
            api_key_to_use = custom_api_key
            device_id_to_use = custom_device_id

        # 验证必要的参数
        if not base_url or not model:
            yield "错误: 请配置base_url和model"
            return

        if not command.strip():
            yield "错误: 请输入命令"
            return

        # 检查智谱AI服务的API Key
        if base_url == "https://open.bigmodel.cn/api/paas/v4" and not api_key_to_use:
            yield "错误: 使用智谱AI服务必须提供API Key"
            return

        # 显示命令信息
        cmd_info = f"执行命令: {command}\n模型: {model}\nBase URL: {base_url}"
        if api_key_to_use:
            cmd_info += f"\nAPI Key: {api_key_to_use[:10]}..."
        if device_id_to_use:
            cmd_info += f"\n设备ID: {device_id_to_use}"

        accumulated_output = f"{cmd_info}\n{'='*50}\n"
        yield accumulated_output

        # 流式执行命令 - 累积式输出
        for chunk in autoglm.execute_command_stream(
            command=command,
            base_url=base_url,
            model=model,
            api_key=api_key_to_use,
            device_id=device_id_to_use
        ):
            if chunk.strip():  # 只处理非空输出
                accumulated_output += chunk + "\n"
                yield accumulated_output

    except Exception as e:
        yield f"执行失败: {str(e)}"

def run_autoglm_command(command: str, use_preset: bool, preset_base_url: str, preset_model: str,
                        api_key: str, device_id: str, custom_base_url: str, custom_model: str,
                        custom_api_key: str, custom_device_id: str, progress=gr.Progress()):
    """运行AutoGLM命令的包装函数（保持兼容性）"""
    result = ""
    for chunk in run_autoglm_command_stream(
        command, use_preset, preset_base_url, preset_model,
        api_key, device_id, custom_base_url, custom_model,
        custom_api_key, custom_device_id
    ):
        result += chunk + "\n"
        progress(min(0.9, len(result) / 1000), desc="正在执行命令...")

    progress(1.0, desc="完成!")
    return result

def create_ui():
    """创建Gradio界面"""
    autoglm = AutoGLMInterface()

    with gr.Blocks(title="AutoGLM - Android设备自动化",
                   head="""
    <style>
        /* 修复输出结果区域的双滚动条问题 */
        #result_output {
            overflow: hidden !important;
            resize: none !important;
        }

        #result_output .gradio-textbox {
            height: 400px !important;
            overflow-y: auto !important;
            resize: none !important;
        }

        #result_output textarea {
            height: 100% !important;
            overflow-y: auto !important;
            resize: none !important;
            scrollbar-width: thin; /* Firefox */
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
        }

        #result_output textarea::-webkit-scrollbar {
            width: 8px;
        }

        #result_output textarea::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 4px;
        }

        #result_output textarea::-webkit-scrollbar-thumb {
            background: #c1c1c1;
            border-radius: 4px;
        }

        #result_output textarea::-webkit-scrollbar-thumb:hover {
            background: #a8a8a8;
        }

        /* 修复输出结果框的样式 */
        .output-result {
            overflow: hidden !important;
        }

        .output-result .gradio-textbox {
            height: 400px !important;
            overflow-y: auto !important;
            resize: none !important;
            border: 1px solid #d1d5db !important;
        }

        .status-card textarea {
            font-family: monospace;
            font-size: 0.9rem;
        }

        .gradio-container {
            max-width: 1920px !important;
            width: 100% !important;
        }

        /* 确保行占满宽度 */
        .gradio-container .wrap {
            width: 100% !important;
        }

        .gradio-container > .gap-2 {
            width: 100% !important;
        }
    </style>
    <script>
        // 全局自动滚动控制
        let autoScrollEnabled = true;
        let isStreaming = false;
        let streamingTimeout = null;
        let autoScrollButton = null;

        // 查找并设置自动滚动按钮
        function setupAutoScrollButton() {
            // 查找所有按钮
            const allButtons = document.querySelectorAll('button');

            allButtons.forEach(btn => {
                // 通过value属性或文本来识别自动滚动按钮
                if (btn.value === 'toggle_autoscroll' ||
                    (btn.textContent && btn.textContent.includes('自动滚动'))) {

                    autoScrollButton = btn;

                    // 设置初始状态
                    btn.textContent = autoScrollEnabled ? '自动滚动: 开启' : '自动滚动: 关闭';
                    btn.style.backgroundColor = autoScrollEnabled ? '' : '#ff6b6b';

                    // 移除旧的事件监听器
                    btn.replaceWith(btn.cloneNode(true));

                    // 重新获取按钮并添加事件
                    const newBtn = document.querySelector('button[value="toggle_autoscroll"]') ||
                                   Array.from(document.querySelectorAll('button')).find(b =>
                                       b.textContent && b.textContent.includes('自动滚动'));

                    if (newBtn) {
                        newBtn.addEventListener('click', function(e) {
                            e.preventDefault();
                            e.stopPropagation();

                            autoScrollEnabled = !autoScrollEnabled;
                            this.textContent = autoScrollEnabled ? '自动滚动: 开启' : '自动滚动: 关闭';
                            this.style.backgroundColor = autoScrollEnabled ? '' : '#ff6b6b';

                            console.log('自动滚动状态切换为:', autoScrollEnabled ? '开启' : '关闭');

                            // 如果关闭了自动滚动，立即停止流式状态
                            if (!autoScrollEnabled) {
                                isStreaming = false;
                                clearTimeout(streamingTimeout);
                            }
                        });

                        console.log('自动滚动按钮已设置');
                    }
                }
            });
        }

        // 简化的滚动实现
        function setupSmartScroll() {
            // 查找结果输出框
            const resultTextarea = document.querySelector('textarea#result_output') ||
                                  document.querySelector('textarea[data-testid*="result_output"]') ||
                                  Array.from(document.querySelectorAll('textarea')).find(ta =>
                                      ta.closest('#result_output') ||
                                      ta.id === 'result_output' ||
                                      (ta.getAttribute('data-testid') && ta.getAttribute('data-testid').includes('result_output'))
                                  );

            if (!resultTextarea) {
                console.log('未找到结果输出框');
                return;
            }

            console.log('找到结果输出框，设置自动滚动');

            let lastValue = resultTextarea.value;
            let lastLength = resultTextarea.value.length;

            // 监听值变化
            function checkValueChange() {
                const currentValue = resultTextarea.value;
                const currentLength = currentValue.length;

                // 如果内容增加了，说明有新输出
                if (currentLength > lastLength && currentValue !== lastValue) {
                    console.log('检测到新内容，长度:', currentLength, '之前长度:', lastLength);

                    // 开始流式输出状态
                    isStreaming = true;
                    clearTimeout(streamingTimeout);

                    // 重置流式输出计时器
                    streamingTimeout = setTimeout(() => {
                        isStreaming = false;
                        console.log('流式输出结束');
                    }, 1500); // 1.5秒没有新内容则认为结束

                    // 如果启用自动滚动，滚动到底部
                    if (autoScrollEnabled) {
                        setTimeout(() => {
                            resultTextarea.scrollTop = resultTextarea.scrollHeight;
                            console.log('已滚动到底部，scrollHeight:', resultTextarea.scrollHeight);
                        }, 50);
                    }
                }

                lastValue = currentValue;
                lastLength = currentLength;
            }

            // 使用多种方式监听变化
            const observer = new MutationObserver(checkValueChange);
            observer.observe(resultTextarea, {
                attributes: true,
                attributeFilter: ['value'],
                childList: true,
                subtree: true,
                characterData: true
            });

            // 监听输入事件
            resultTextarea.addEventListener('input', checkValueChange);
            resultTextarea.addEventListener('change', checkValueChange);
            resultTextarea.addEventListener('keyup', checkValueChange);

            // 定时检查（兜底方案）
            setInterval(checkValueChange, 200);

            console.log('自动滚动监听器已设置');
        }

        // 初始化函数
        function initializeAutoScroll() {
            console.log('初始化自动滚动');
            setupAutoScrollButton();
            setupSmartScroll();
        }

        // 确保DOM加载完成后执行
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initializeAutoScroll);
        } else {
            initializeAutoScroll();
        }

        // 页面加载完成后再次尝试
        window.addEventListener('load', function() {
            setTimeout(initializeAutoScroll, 1000);
        });

        // 监听DOM变化，重新初始化
        const observer = new MutationObserver(function(mutations) {
            let shouldReinit = false;
            mutations.forEach(mutation => {
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeName === 'BUTTON' || (node.querySelector && node.querySelector('button'))) {
                            shouldReinit = true;
                        }
                    });
                }
            });

            if (shouldReinit) {
                setTimeout(initializeAutoScroll, 500);
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    </script>
                   """) as demo:

        # 标题和说明
        gr.Markdown("""
        # 🤖 AutoGLM Web界面

        智能Android设备自动化操作平台 - 通过自然语言控制您的Android设备
        """, elem_classes=["header"])

        with gr.Row():
            # 第一列：设备状态
            with gr.Column(scale=2, min_width=280):
                gr.Markdown("### 设备状态")
                status_btn = gr.Button("检查状态", variant="secondary", size="lg")
                status_text = gr.Textbox(label="连接状态", interactive=False, elem_classes=["status-card"])
                status_detail = gr.Textbox(label="设备详细信息", interactive=False, elem_classes=["status-card"], lines=6)

                # 支持的应用部分
                gr.Markdown("### 支持的应用", visible=True)
                apps_btn = gr.Button("获取应用列表", size="sm")
                apps_list = gr.Textbox(label="可用应用", interactive=False, lines=8, max_lines=12)

            # 第二列：命令输入和执行结果
            with gr.Column(scale=6, min_width=600):
                gr.Markdown("### 命令输入")

                # 命令示例
                with gr.Accordion("命令示例", open=False):
                    gr.Markdown("""
                    - "打开美团搜索附近的火锅店"
                    - "发送微信消息给张三"
                    - "打开抖音并搜索美食视频"
                    - "设置明天早上8点的闹钟"
                    - "拍照并发送给联系人"
                    """)

                command_input = gr.Textbox(
                    label="输入您的命令",
                    placeholder="例如：打开美团搜索附近的火锅店",
                    lines=3
                )

                execute_btn = gr.Button("执行命令", variant="primary", size="lg")

                # 执行结果
                gr.Markdown("### 执行结果")
                result_output = gr.Textbox(
                    label="输出结果",
                    interactive=False,
                    lines=30,
                    max_lines=50,
                    elem_id="result_output",
                    elem_classes=["output-result"],
                    container=True
                )

                with gr.Row():
                    clear_btn = gr.Button("清空结果", size="sm")
                    copy_btn = gr.Button("复制结果", size="sm")
                    auto_scroll_btn = gr.Button("自动滚动: 开启", size="sm", value="toggle_autoscroll")

            # 第三列：模型配置
            with gr.Column(scale=2, min_width=320):
                gr.Markdown("### 模型配置")

                # 使用Radio按钮选择配置类型
                config_type = gr.Radio(
                    choices=["智谱AI服务(推荐)", "自定义模型服务"],
                    value="智谱AI服务(推荐)",
                    label="选择配置类型"
                )

                # 根据选择显示不同配置
                with gr.Group(visible=True) as preset_group:
                    gr.Markdown("""
                    ### 智谱AI官方服务
                    使用智谱AI提供的AutoGLM服务，需要获取API Key

                    **获取API Key:**
                    1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
                    2. 注册并登录账号
                    3. 创建API Key
                    """)

                    # 固定的智谱AI配置
                    preset_base_url = gr.Textbox(
                        value="https://open.bigmodel.cn/api/paas/v4",
                        visible=False
                    )
                    preset_model = gr.Textbox(
                        value="autoglm-phone",
                        visible=False
                    )

                    # API Key输入框
                    api_key = gr.Textbox(
                        label="API Key (必填)",
                        type="password",
                        placeholder="请输入您的智谱AI API Key"
                    )

                    device_id = gr.Textbox(
                        label="设备ID (可选)",
                        placeholder="多设备时指定",
                        value=""
                    )

                with gr.Group(visible=False) as custom_group:
                    gr.Markdown("""
                    ### 自定义模型服务
                    如果您有自己的模型服务，可以在此配置
                    """)

                    custom_base_url = gr.Textbox(
                        label="Base URL",
                        placeholder="http://localhost:8000/v1"
                    )
                    custom_model = gr.Textbox(
                        label="模型名称",
                        placeholder="autoglm-phone-9b"
                    )
                    custom_api_key = gr.Textbox(
                        label="API Key (可选)",
                        type="password",
                        placeholder="如果需要请输入"
                    )
                    custom_device_id = gr.Textbox(
                        label="设备ID (可选)",
                        placeholder="多设备时指定"
                    )

                # 根据选择的类型显示/隐藏对应组
                def toggle_config(choice):
                    if choice == "智谱AI服务(推荐)":
                        return gr.update(visible=True), gr.update(visible=False), True
                    else:
                        return gr.update(visible=False), gr.update(visible=True), False

                config_state = gr.State(value=True)  # True表示使用预设(智谱AI)，False表示使用自定义

                config_type.change(
                    fn=toggle_config,
                    inputs=[config_type],
                    outputs=[preset_group, custom_group, config_state]
                )

        # 事件绑定
        status_btn.click(
            fn=autoglm.check_device_status,
            outputs=[status_text, status_detail]
        )

        apps_btn.click(
            fn=autoglm.get_available_apps,
            outputs=[apps_list]
        )

        execute_btn.click(
            fn=run_autoglm_command_stream,
            inputs=[
                command_input,
                config_state,
                preset_base_url,
                preset_model,
                api_key,
                device_id,
                custom_base_url,
                custom_model,
                custom_api_key,
                custom_device_id
            ],
            outputs=[result_output],
            show_progress=True
        )

        # 清空和复制功能
        clear_btn.click(
            fn=lambda: ("", ""),
            outputs=[command_input, result_output]
        )

        copy_btn.click(
            fn=lambda text: gr.update(value=text),
            inputs=[result_output],
            outputs=[result_output]
        )

        # 初始化时检查设备状态
        demo.load(
            fn=autoglm.check_device_status,
            outputs=[status_text, status_detail]
        )

    return demo


if __name__ == "__main__":
    # 创建CSS样式（基础样式）
    css = """
    .header {
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }

    .status-card {
        border: 2px solid #e1e5e9;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        background: #f8f9fa;
    }

    .container {
        max-width: 1200px;
        margin: 0 auto;
    }

    /* 优化状态显示 */
    .status-card textarea {
        font-family: monospace;
        font-size: 0.9rem;
    }

    /* 调整整体布局 */
    .gradio-container {
        max-width: 1920px !important;
        width: 100% !important;
    }
    """

    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=8865,
        share=False,
        debug=True,
        theme=gr.themes.Soft(),
        css=css
    )