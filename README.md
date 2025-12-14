# Open-AutoGLM

[Readme in English](README_en.md)

基于https://github.com/zai-org/Open-AutoGLM 使用Gradio，增加了webui页面

## 懒人版快速安装

你可以使用Claude Code，配置 [GLM Coding Plan](https://bigmodel.cn/glm-coding) 后，输入以下提示词，快速部署本项目。

```
访问文档，为我安装 AutoGLM
https://raw.githubusercontent.com/zai-org/Open-AutoGLM/refs/heads/main/README.md
```

## 项目介绍

Open-AutoGLM 是一个基于 AutoGLM 构建的手机端智能助理框架，它能够以多模态方式理解手机屏幕内容，并通过自动化操作帮助用户完成任务。系统通过 ADB(Android Debug Bridge)来控制设备，以视觉语言模型进行屏幕感知，再结合智能规划能力生成并执行操作流程。用户只需用自然语言描述需求，如"打开小红书搜索美食"，Open-AutoGLM 即可自动解析意图、理解当前界面、规划下一步动作并完成整个流程。系统还内置敏感操作确认机制，并支持在登录或验证码场景下进行人工接管。同时，它提供远程 ADB 调试能力，可通过 WiFi 或网络连接设备，实现灵活的远程控制与开发。

> ⚠️
> 本项目仅供研究和学习使用。严禁用于非法获取信息、干扰系统或任何违法活动。请仔细审阅 [使用条款](resources/privacy_policy.txt)。

## 🚀 快速开始

### 方式一：Web 界面（推荐）/作者增加的

我们提供了现代化的 Web 界面，让操作更加便捷：

```bash
# 1. 安装依赖
pip install -r requirements.txt
pip install -e .

# 2. 启动 Web UI
python start_web_ui.py

# 3. 访问 http://localhost:8865
```

### 方式二：联合启动（Web UI + scrcpy屏幕镜像）/作者增加的

使用我们的一键启动脚本，同时启动 Web 界面和屏幕镜像：

```bash
# Windows 用户
双击运行 start_all.bat

# 或使用 Python 脚本
python start_all.py
```

启动后将会：
- 自动打开 Web 界面 (http://localhost:8865)
- 启动 scrcpy 屏幕镜像窗口
- 支持同时进行智能控制和手动操作

### 方式三：命令行/代码原生

```bash
# 交互模式---本地部署
python main.py --base-url http://localhost:8000/v1 --model "autoglm-phone-9b"   

# 单次执行---本地部署
python main.py --base-url http://localhost:8000/v1 "打开美团搜索附近的火锅店"

# 使用智谱 BigModel
python main.py --base-url https://open.bigmodel.cn/api/paas/v4 --model "autoglm-phone" --apikey "your-bigmodel-api-key" "打开美团搜索附近的火锅店"

# 使用 ModelScope
python main.py --base-url https://api-inference.modelscope.cn/v1 --model "ZhipuAI/AutoGLM-Phone-9B" --apikey "your-modelscope-api-key" "打开美团搜索附近的火锅店"
```

## 📱 模型下载地址

| Model                         | Download Links                                                                                                                                                         |
|-------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| AutoGLM-Phone-9B              | [🤗 Hugging Face](https://huggingface.co/zai-org/AutoGLM-Phone-9B)<br>[🤖 ModelScope](https://modelscope.cn/models/ZhipuAI/AutoGLM-Phone-9B)                           |
| AutoGLM-Phone-9B-Multilingual | [🤗 Hugging Face](https://huggingface.co/zai-org/AutoGLM-Phone-9B-Multilingual)<br>[🤖 ModelScope](https://modelscope.cn/models/ZhipuAI/AutoGLM-Phone-9B-Multilingual) |

- `AutoGLM-Phone-9B`：针对中文手机应用优化的模型
- `AutoGLM-Phone-9B-Multilingual`：支持英语场景的多语言模型

## ⚙️ 环境准备

### 1. Python 环境

建议使用 Python 3.10 及以上版本。

### 2. ADB (Android Debug Bridge)

1. 下载官方 ADB [安装包](https://developer.android.com/tools/releases/platform-tools?hl=zh-cn)，并解压到自定义路径
2. 配置环境变量

**MacOS 配置：**
```bash
export PATH=${PATH}:~/Downloads/platform-tools
```

**Windows 配置：**
参考 [第三方教程](https://blog.csdn.net/x2584179909/article/details/108319973) 进行配置。

### 3. Android 设备准备

- Android 7.0+ 的设备或模拟器
- 启用 `开发者模式` 和 `USB 调试`
- 部分机型需要同时开启 `USB 调试(安全设置)`
- 然后需要到手机的开发者设置中开启 USB 调试，小米系手机还需要额外开启 USB 调试（安全设置），这个选项要求手机必须插入 SIM 卡才能开启，开启后可以移除 SIM 卡。

### 4. 安装 ADB Keyboard（用于文本输入）

-下载 [ADBKeyboard.apk](https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk) 并安装到安卓设备。

-APK文件已经放在项目文件夹下

-下载 [ADBKeyboard.apk](https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk) 并安装到安卓设备。

-APK文件已经放在项目文件夹下

### 5. 安装 scrcpy（用于显示手机中的屏幕）

项目地址：https://github.com/Genymobile/scrcpy

这是一个在电脑上显示手机屏幕的工具。使用这个工具可以直接在电脑屏幕上监视手机屏幕，比较方便。

确保手机连接到电脑，从 Release 中下载最新包，解压后运行 scrcpy-console.bat （实际就是打开scrcpy.exe）后应当可以看到手机的投屏。

项目中已经放了文件夹：scrcpy-win64-v3.3.3

使用我的一键启动则会自动连接


## 🎯 模型服务配置

### 选项 A：使用第三方模型服务（强烈推荐）

**智谱 BigModel：现在免费**
- 文档: https://docs.bigmodel.cn/cn/api/introduction
- `--base-url`: `https://open.bigmodel.cn/api/paas/v4`
- `--model`: `autoglm-phone`
- `--apikey`: 在智谱平台申请 API Key

**ModelScope(魔搭社区)：**
- 文档: https://modelscope.cn/models/ZhipuAI/AutoGLM-Phone-9B
- `--base-url`: `https://api-inference.modelscope.cn/v1`
- `--model`: `ZhipuAI/AutoGLM-Phone-9B`
- `--apikey`: 在 ModelScope 平台申请 API Key

### 选项 B：本地部署模型

需要 NVIDIA GPU (建议24GB+显存)：我的4090还没试过

```bash
# 使用 vLLM 部署
python3 -m vllm.entrypoints.openai.api_server \
 --served-model-name autoglm-phone-9b \
 --allowed-local-media-path /   \
 --mm-encoder-tp-mode data \
 --mm_processor_cache_type shm \
 --mm_processor_kwargs "{\"max_pixels\":5000000}" \
 --max-model-len 25480  \
 --chat-template-content-format string \
 --limit-mm-per-prompt "{\"image\":10}" \
 --model zai-org/AutoGLM-Phone-9B \
 --port 8000
```

## 🖥️ Web UI 特性

我们的 Web 界面提供了丰富的功能：

### 三列布局设计
- **左列**：设备状态管理
  - 实时检查 ADB 连接状态
  - 查看设备详细信息
  - 获取可用应用列表

- **中列**：命令执行中心
  - 自然语言命令输入
  - 实时执行结果展示
  - 智能自动滚动功能

- **右列**：模型配置
  - 支持预设和自定义配置
  - 灵活的 API 参数设置
  - 多设备管理选项

### 核心功能
- **📱 实时设备状态检查** - 检查 ADB 连接和设备状态
- **⚙️ 灵活的模型配置** - 支持智谱AI、自定义服务等
- **💬 直观的命令输入** - 自然语言输入命令
- **📊 实时输出显示** - 查看 AI 的执行过程和结果
- **🔄 智能滚动** - 自动跟随最新输出，支持手动控制
- **📋 应用列表查看** - 查看所有支持的应用

## 🌐 远程调试

Open-AutoGLM 支持通过 WiFi/网络进行远程 ADB 调试：

### 配置步骤

1. **手机端开启无线调试**
   - 确保手机和电脑在同一 WiFi 网络
   - 开发者选项 → 网络ADB调试

2. **连接设备**
```bash
# 通过 WiFi 连接
adb connect 192.168.1.100:5555

# 验证连接
adb devices

# 指定远程设备执行任务
python main.py --device-id 192.168.1.100:5555 --base-url http://localhost:8000/v1 "打开抖音"
```

## 📚 使用示例

### Web UI 使用示例

1. **打开网页**：访问 http://localhost:8865
2. **配置模型**：选择"智谱AI服务(推荐)"，输入您的 API Key
3. **检查设备**：点击"检查状态"按钮
4. **执行命令**：输入"打开美团搜索附近的火锅店"，点击"执行命令"

### 命令行使用示例

```bash
# 使用智谱 BigModel
python main.py --base-url https://open.bigmodel.cn/api/paas/v4 --model "autoglm-phone" --apikey "your-api-key" "打开美团搜索附近的火锅店"

# 交互模式
python main.py --base-url http://localhost:8000/v1 --model "autoglm-phone-9b"

# 列出支持的应用
python main.py --list-apps

# 远程设备控制
python main.py --device-id 192.168.1.100:5555 --base-url http://localhost:8000/v1 "打开微信"
```

### Python API 使用

```python
from phone_agent import PhoneAgent
from phone_agent.model import ModelConfig

# 配置模型
model_config = ModelConfig(
    base_url="http://localhost:8000/v1",
    model_name="autoglm-phone-9b",
)

# 创建 Agent
agent = PhoneAgent(model_config=model_config)

# 执行任务
result = agent.run("打开淘宝搜索无线耳机")
print(result)
```

## 🎮 支持的应用

Open-AutoGLM 支持 50+ 款主流中文应用：

| 分类   | 应用              |
|------|-----------------|
| 社交通讯 | 微信、QQ、微博        |
| 电商购物 | 淘宝、京东、拼多多       |
| 美食外卖 | 美团、饿了么、肯德基      |
| 出行旅游 | 携程、12306、滴滴出行   |
| 视频娱乐 | bilibili、抖音、爱奇艺 |
| 音乐音频 | 网易云音乐、QQ音乐、喜马拉雅 |
| 生活服务 | 大众点评、高德地图、百度地图  |
| 内容社区 | 小红书、知乎、豆瓣       |

运行 `python main.py --list-apps` 查看完整列表。

## 🔧 高级配置

### 环境变量

| 变量                      | 描述               | 默认值                        |
|-------------------------|------------------|----------------------------|
| `PHONE_AGENT_BASE_URL`  | 模型 API 地址        | `http://localhost:8000/v1` |
| `PHONE_AGENT_MODEL`     | 模型名称             | `autoglm-phone-9b`         |
| `PHONE_AGENT_API_KEY`   | 模型认证 API Key     | `EMPTY`                    |
| `PHONE_AGENT_MAX_STEPS` | 每个任务最大步数         | `100`                      |
| `PHONE_AGENT_DEVICE_ID` | ADB 设备 ID        | (自动检测)                     |
| `PHONE_AGENT_LANG`      | 语言 (`cn` 或 `en`) | `cn`                       |

### 自定义回调

```python
def my_confirmation(message: str) -> bool:
    """敏感操作确认回调"""
    return input(f"确认执行 {message}？(y/n): ").lower() == "y"

def my_takeover(message: str) -> None:
    """人工接管回调"""
    print(f"请手动完成: {message}")
    input("完成后按回车继续...")

agent = PhoneAgent(
    confirmation_callback=my_confirmation,
    takeover_callback=my_takeover,
)
```

## ❓ 常见问题

### 设备连接问题

**设备未找到：**
```bash
adb kill-server
adb start-server
adb devices
```

**能打开应用但无法点击：**
- 确保同时开启「USB 调试」和「USB 调试(安全设置)」
- 检查数据线是否支持数据传输

### 文本输入问题

**中文输入不工作：**
1. 确保设备已安装 ADB Keyboard
2. 在系统设置中启用 ADB Keyboard
3. Agent 会自动切换输入法

### Windows 编码问题

**报错 `UnicodeEncodeError gbk code`：**
```bash
set PYTHONIOENCODING=utf-8
python main.py [你的参数]
```

## 📂 项目结构

```
Open-AutoGLM/
├── main.py              # 主程序入口
├── start_web_ui.py      # Web UI 启动脚本
├── start_all.bat        # Windows 一键启动脚本
├── start_all.py         # Python 联合启动脚本
├── web_ui/              # Web UI 模块
│   ├── app.py          # Web 界面实现
│   └── README.md       # Web UI 说明
├── phone_agent/         # 核心模块
│   ├── agent.py        # PhoneAgent 主类
│   ├── adb/            # ADB 工具
│   ├── actions/        # 操作处理
│   ├── config/         # 配置文件
│   └── model/          # AI 模型客户端
├── examples/           # 示例代码
├── scripts/            # 辅助脚本
└── resources/          # 资源文件
```

## 🔍 故障排除

| 错误现象 | 可能原因 | 解决方案 |
|---------|---------|---------|
| `adb devices` 无输出 | USB 调试未开启或数据线问题 | 检查开发者选项，更换数据线 |
| `adb devices` 显示 unauthorized | 手机未授权 | 手机上点击「允许 USB 调试」|
| 能打开应用但无法点击 | 缺少安全调试权限 | 开启「USB 调试(安全设置)」|
| 中文输入变成乱码 | ADB Keyboard 未启用 | 在系统设置中启用 ADB Keyboard |
| 截图返回黑屏 | 敏感页面(支付/银行) | 正常现象，系统会自动处理 |
| Web UI 无法访问 | 端口被占用 | 使用其他端口或关闭占用进程 |
| scrcpy 无法启动 | 设备未连接或驱动问题 | 检查 ADB 连接和设备驱动 |

## 📖 文档

- [Web UI 使用指南](启动说明.md)
- [二次开发指南](README_coding_agent.md)
- [API 文档](docs/api.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！请查看 [贡献指南](CONTRIBUTING.md) 了解详情。

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

## 🙏 致谢

感谢所有为本项目做出贡献的开发者和用户！

## 📚 参考文献

如果你觉得我们的工作有帮助，请引用以下论文：

```bibtex
@article{liu2024autoglm,
  title={Autoglm: Autonomous foundation agents for guis},
  author={Liu, Xiao and Qin, Bo and Liang, Dongzhu and Dong, Guang and Lai, Hanyu and Zhang, Hanchen and Zhao, Hanlin and Iong, Iat Long and Sun, Jiadai and Wang, Jiaqi and others},
  journal={arXiv preprint arXiv:2411.00820},
  year={2024}
}
@article{xu2025mobilerl,
  title={MobileRL: Online Agentic Reinforcement Learning for Mobile GUI Agents},
  author={Xu, Yifan and Liu, Xiao and Liu, Xinghan and Fu, Jiaqi and Zhang, Hanchen and Jing, Bohao and Zhang, Shudan and Wang, Yuting and Zhao, Wenyi and Dong, Yuxiao},
  journal={arXiv preprint arXiv:2509.18119},
  year={2025}
}
```

---

## 🚀 自动化部署指南(面向 AI)

> **本章节专为 AI 助手(如 Claude Code)设计，用于自动化部署 Open-AutoGLM。**
>
> 如果你是人类读者，可以跳过本章节，按照上面的文档操作即可。

### 部署前置检查

在开始部署前，请逐项向用户确认以下内容：

#### 硬件环境
- [ ] 用户有一台安卓手机(Android 7.0+)
- [ ] 用户有一根支持数据传输的 USB 数据线
- [ ] 手机和电脑可以通过数据线连接

#### 手机端配置
- [ ] 手机已开启「开发者模式」
- [ ] 手机已开启「USB 调试」
- [ ] 部分机型需要同时开启「USB 调试(安全设置)」
- [ ] 手机已安装 ADB Keyboard 应用
- [ ] ADB Keyboard 已在系统设置中启用

#### 模型服务确认
**请明确询问用户：你是否已有可用的 AutoGLM 模型服务？**

- **选项 A：使用已部署的模型服务(推荐)**
  - 用户提供模型服务的 URL
  - 无需本地 GPU，无需下载模型

- **选项 B：本地部署模型(高配置要求)**
  - 需要 NVIDIA GPU(建议 24GB+ 显存)
  - 需要安装 vLLM 或 SGLang

### 部署流程

#### 阶段一：环境准备
```bash
# 1. 验证 ADB 安装
adb version

# 2. 连接手机并验证
adb devices
```

#### 阶段二：安装 Agent
```bash
# 1. 克隆仓库
git clone https://github.com/zai-org/Open-AutoGLM.git
cd Open-AutoGLM

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt
pip install -e .
```

#### 阶段三：启动服务
```bash
# 启动 Web UI
python start_web_ui.py

# 或使用联合启动
python start_all.py
```

#### 阶段四：验证部署
```bash
# 验证命令是否正常工作
python main.py --base-url {MODEL_URL} --model "autoglm-phone-9b" "打开微信，对文件传输助手发送消息：部署成功"

python main.py --base-url https://open.bigmodel.cn/api/paas/v4 --model "autoglm-phone" --apikey "your-bigmodel-api-key" "打开微信，对文件传输助手发送消息：部署成功"
```

**预期结果：**
- 手机自动打开微信
- 自动搜索「文件传输助手」
- 自动发送消息「部署成功」

---

**部署完成的标志：手机能自动执行用户的自然语言指令。**