@echo off
title AutoGLM + scrcpy 联合启动器
chcp 65001 > nul

echo ========================================
echo AutoGLM + scrcpy 联合启动器
echo ========================================
echo.

echo 正在启动AutoGLM Web UI...
start "AutoGLM Web UI" /MIN python start_web_ui.py

echo 等待Web UI启动...
timeout /t 5 /nobreak > nul

echo.
echo 正在启动scrcpy屏幕镜像...
start "scrcpy屏幕镜像" "scrcpy-win64-v3.3.3\scrcpy.exe"

echo.


echo.
echo ========================================
echo 启动完成！
echo ========================================
echo.
echo 1. Web界面:
echo    - 已自动打开: http://localhost:8865
echo    - 用于AutoGLM智能控制
echo    - 输入自然语言命令控制设备
echo.
echo 2. scrcpy屏幕镜像:
echo    - 独立窗口显示设备屏幕
echo    - 支持鼠标和键盘直接控制
echo.
echo 两个程序可以同时使用：
echo - Web界面用于智能语音控制
echo - scrcpy窗口用于手动操作
echo.
echo 关闭此窗口不会影响已启动的程序
echo 要停止程序，请关闭各自的控制台窗口
echo ========================================
pause