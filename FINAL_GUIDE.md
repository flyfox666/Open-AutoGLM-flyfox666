# AutoGLM 使用指南

## ✅ 已完成的工作

1. **修复了所有Unicode编码问题**
   - 移除了所有emoji字符，避免Windows系统编码错误
   - 包括 main.py、agent.py、client.py 等文件

2. **创建了Web UI界面**
   - 基于Gradio的现代化界面
   - 支持智谱AI和自定义模型配置
   - 自动端口检测（8865, 8861, 8862, 8960）

3. **路径问题修复**
   - Web UI能正确找到并执行main.py
   - 不再依赖硬编码路径

## 🚀 使用方法

### 方法1：命令行（推荐，最稳定）

```bash
python main.py --base-url https://open.bigmodel.cn/api/paas/v4 --model "autoglm-phone" --apikey "您的APIKey" "您的指令"
```

示例：
```bash
python main.py --base-url https://open.bigmodel.cn/api/paas/v4 --model "autoglm-phone" --apikey "91cf178671984a5ab118ad9e7987c185.VVP8yQ3fVifG5Gqs" "打开大众点评"
```

### 方法2：Web UI

1. 启动Web UI：
   ```bash
   python start_web_ui.py
   ```

2. 如果端口被占用，可以指定端口：
   ```bash
   set GRADIO_SERVER_PORT=8888
   python start_web_ui.py
   ```

3. 在浏览器中访问显示的地址（如 http://localhost:8865）

4. 配置：
   - 选择"智谱AI服务(推荐)"
   - 输入您的API Key
   - 点击执行命令

## 🔑 获取API Key

1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
2. 注册并登录
3. 进入控制台
4. 创建API Key
5. 复制生成的API Key（格式如：sk-xxxxxxxx...）

## 📱 支持的命令示例

- "打开美团搜索附近的火锅店"
- "打开大众点评"
- "发送微信消息给张三"
- "打开抖音并搜索美食视频"
- "设置明天早上8点的闹钟"
- "拍照并发送给联系人"

## ⚠️ 注意事项

1. **确保ADB已安装并配置**
   - Windows: 下载 platform-tools 并添加到PATH
   - 验证命令：`adb devices`

2. **确保手机已连接**
   - 开启USB调试
   - 安装ADB Keyboard
   - 在设置中启用ADB Keyboard

3. **Windows控制台乱码问题**
   - 这是显示问题，不影响功能
   - 可以使用 `chcp 65001` 切换编码（可选）

4. **端口占用**
   - 关闭其他Gradio实例
   - 或使用环境变量指定不同端口

## 🎉 成功标志

当您看到类似以下输出时，表示系统正常工作：
```
OK - All system checks passed!
OK - Model API checks passed!
Phone Agent - AI-powered phone automation
==================================================
```

手机会自动执行您的指令！

## 🆘 故障排除

| 问题 | 解决方案 |
|------|----------|
| UnicodeEncodeError | 已修复，如还有问题请重启终端 |
| 端口被占用 | 使用不同端口或关闭占用程序 |
| ADB设备未找到 | 检查USB调试和数据线 |
| API调用失败 | 检查API Key和网络连接 |