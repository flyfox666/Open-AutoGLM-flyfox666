#!/usr/bin/env python3
"""
同时启动AutoGLM Web UI和scrcpy屏幕镜像
"""

import os
import sys
import subprocess
import threading
import time
import webbrowser
from pathlib import Path

def check_dependencies():
    """检查依赖是否安装"""
    try:
        import gradio as gr
        print("[OK] Gradio已安装")
    except ImportError:
        print("[ERROR] Gradio未安装，请运行: pip install -r requirements.txt")
        return False

    try:
        import PIL
        print("[OK] Pillow已安装")
    except ImportError:
        print("[ERROR] Pillow未安装，请运行: pip install -r requirements.txt")
        return False

    return True

def check_scrcpy():
    """检查scrcpy程序是否存在"""
    scrcpy_path = Path("scrcpy-win64-v3.3.3/scrcpy.exe")
    if scrcpy_path.exists():
        print(f"[OK] scrcpy程序已找到: {scrcpy_path}")
        return str(scrcpy_path.absolute())
    else:
        print("[WARNING] scrcpy程序未找到")
        print(f"   期望路径: {scrcpy_path.absolute()}")
        return None

def start_web_ui():
    """启动Web UI"""
    print("\n" + "="*50)
    print("启动AutoGLM Web UI...")
    print("="*50)

    # 检查web_ui目录是否存在
    web_ui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_ui")
    if not os.path.exists(web_ui_dir):
        print("[ERROR] web_ui目录不存在")
        return None

    # 将web_ui目录添加到Python路径
    sys.path.insert(0, web_ui_dir)

    try:
        from app import create_ui
        demo = create_ui()

        # 尝试多个端口
        ports = [8865, 8861, 8862, 8960]
        for port in ports:
            try:
                print(f"Web UI访问地址: http://localhost:{port}")

                # 在新线程中启动Web UI
                def launch_server():
                    demo.launch(
                        server_name="0.0.0.0",
                        server_port=port,
                        share=False,
                        show_error=True,
                        quiet=False
                    )

                server_thread = threading.Thread(target=launch_server, daemon=True)
                server_thread.start()

                # 等待服务器启动
                time.sleep(2)

                # 自动打开浏览器
                print(f"正在打开Web界面...")
                webbrowser.open(f"http://localhost:{port}")

                return port
            except Exception as e:
                if f"Port {port}" in str(e) or "already in use" in str(e):
                    print(f"端口 {port} 被占用，尝试下一个...")
                    continue
                else:
                    raise
        else:
            print("[ERROR] 所有端口都被占用")
            return None

    except Exception as e:
        print(f"[ERROR] Web UI启动失败: {e}")
        return None

def start_scrcpy(scrcpy_path):
    """启动scrcpy"""
    print(f"\n启动scrcpy屏幕镜像...")
    print(f"scrcpy路径: {scrcpy_path}")

    try:
        # 使用scrcpy-console.bat启动，这样出错时会暂停
        console_bat = Path("scrcpy-win64-v3.3.3/scrcpy-console.bat")

        if console_bat.exists():
            print(f"使用控制台启动器: {console_bat}")
            process = subprocess.Popen(
                [str(console_bat.absolute())],
                cwd=console_bat.parent
            )
        else:
            # 直接启动scrcpy.exe
            print("直接启动scrcpy.exe")
            process = subprocess.Popen(
                [scrcpy_path],
                cwd=Path(scrcpy_path).parent
            )

        print("[OK] scrcpy已启动")
        print("提示: scrcpy窗口将显示设备屏幕")
        print("      可通过鼠标和键盘控制设备")

        return process

    except Exception as e:
        print(f"[ERROR] scrcpy启动失败: {e}")
        return None

def main():
    """主函数"""
    print("="*60)
    print("AutoGLM + scrcpy 联合启动器")
    print("="*60)

    # 检查依赖
    if not check_dependencies():
        print("\n请先安装必要依赖:")
        print("pip install -r requirements.txt")
        input("按回车键退出...")
        return

    # 检查ADB
    print("\n检查ADB连接...")
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and "device" in result.stdout:
            print("[OK] 检测到已连接的Android设备")
        else:
            print("[WARNING] 未检测到Android设备")
            print("请确保:")
            print("1. Android设备已连接USB")
            print("2. 已开启USB调试模式")
            print("3. 已授权此电脑的调试权限")
    except:
        print("[WARNING] ADB未找到，请确保Android SDK Platform Tools已安装并在PATH中")

    # 检查scrcpy
    scrcpy_path = check_scrcpy()

    # 启动Web UI
    web_ui_port = start_web_ui()

    # 启动scrcpy（如果存在）
    scrcpy_process = None
    if scrcpy_path:
        scrcpy_process = start_scrcpy(scrcpy_path)

    # 显示使用说明
    print("\n" + "="*60)
    print("使用说明:")
    print("="*60)
    print("1. Web界面:")
    if web_ui_port:
        print(f"   - 访问: http://localhost:{web_ui_port}")
        print(f"   - 浏览器已自动打开")
    else:
        print("   - Web UI启动失败，请检查错误信息")
    print("   - 用于AutoGLM智能控制")
    print("   - 输入自然语言命令控制设备")
    print("")
    print("2. scrcpy屏幕镜像:")
    if scrcpy_process:
        print("   - 已启动独立的scrcpy窗口")
        print("   - 实时显示设备屏幕")
        print("   - 支持鼠标点击、键盘输入")
    else:
        print("   - scrcpy未启动，请检查程序路径")
    print("")
    print("3. 控制:")
    print("   - Web界面: 语音/文本智能控制")
    print("   - scrcpy窗口: 直接触摸/键盘控制")
    print("")
    print("按 Ctrl+C 停止所有程序")
    print("="*60)

    try:
        # 等待用户中断
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止程序...")

        # 停止scrcpy
        if scrcpy_process:
            try:
                scrcpy_process.terminate()
                print("[OK] scrcpy已停止")
            except:
                pass

        print("[INFO] 所有程序已停止")

if __name__ == "__main__":
    main()