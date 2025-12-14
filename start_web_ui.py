#!/usr/bin/env python3
"""
启动AutoGLM Web UI
"""

import os
import sys

def check_dependencies():
    """检查依赖是否安装"""
    try:
        import gradio as gr
        print("OK - Gradio已安装")
    except ImportError:
        print("ERROR - Gradio未安装，请运行: pip install -r requirements.txt")
        return False

    try:
        import PIL
        print("OK - Pillow已安装")
    except ImportError:
        print("ERROR - Pillow未安装，请运行: pip install -r requirements.txt")
        return False

    return True

def main():
    print("启动AutoGLM Web UI...")

    # 检查依赖
    if not check_dependencies():
        sys.exit(1)

    # 检查ADB
    print("检查ADB连接...")
    try:
        import subprocess
        result = subprocess.run(["adb", "version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("OK - ADB已安装")
        else:
            print("WARNING - ADB未正确安装，请确保ADB已添加到系统PATH")
    except:
        print("WARNING - ADB未找到，请确保ADB已安装并添加到系统PATH")

    # 检查web_ui目录是否存在
    web_ui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_ui")
    if not os.path.exists(web_ui_dir):
        print("ERROR - web_ui目录不存在")
        sys.exit(1)

    # 将web_ui目录添加到Python路径
    sys.path.insert(0, web_ui_dir)

    # 启动Gradio应用
    print("\n正在启动Web界面...")
    print("正在尝试可用端口...")

    try:
        from app import create_ui
        demo = create_ui()
        # 尝试多个端口
        ports = [8865, 8861, 8862, 8960]
        for port in ports:
            try:
                print(f"访问地址: http://localhost:{port}")
                demo.launch(
                    server_name="0.0.0.0",
                    server_port=port,
                    share=False,
                    inbrowser=True,
                    show_error=True,
                    quiet=False
                )
                break
            except Exception as e:
                if f"Port {port}" in str(e) or "already in use" in str(e):
                    print(f"端口 {port} 被占用，尝试下一个...")
                    continue
                else:
                    raise
        else:
            print("ERROR - 所有端口都被占用，请手动关闭其他程序或指定其他端口")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR - 启动失败: {e}")
        print("请确保已安装所有依赖：pip install -r requirements.txt")
        sys.exit(1)

if __name__ == "__main__":
    main()