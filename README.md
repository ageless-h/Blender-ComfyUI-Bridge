# Blender-ComfyUI Bridge

[![GitHub Repo stars](https://img.shields.io/github/stars/ageless-h/Blender-ComfyUI-Bridge?style=social)](https://github.com/ageless-h/Blender-ComfyUI-Bridge/stargazers)

一个Blender插件，作为在Blender和ComfyUI之间进行实时、双向通信的桥梁。

这个插件允许您在Blender中一键将渲染结果或图像数据无缝地发送到ComfyUI中一个预设好的工作流进行处理，然后将处理后的图像自动返回到Blender中。

## ✨ 功能特性

*   **一键发送数据**: 在Blender的3D视图侧边栏中提供一个简洁的UI面板，点击按钮即可渲染当前场景并将图像数据发送到ComfyUI。
*   **强大的图像格式支持**:
    *   **标准图像 (PNG/JPG)**: 快速发送预览图。
    *   **多通道EXR (Multi-Layer EXR)**: 将所有渲染通道 (如 `Depth`, `Mist`, `Normal`, `AO` 等) 无损地打包到一个 EXR 文件中发送，为下游的图像处理提供最大的灵活性。
*   **灵活的网络连接**:
    *   **直接连接**: 在本地网络环境中直接连接到ComfyUI。
    *   **SSH隧道**: 内置SSH隧道功能，允许您通过安全的SSH连接，将本地Blender实例与远程服务器上的ComfyUI无缝对接，无需手动配置端口转发。
*   **智能数据传输**: 插件通过内存直接发送图像的二进制数据，无需共享文件系统，支持跨机器、跨容器的复杂网络环境。
*   **实时连接状态**: UI会实时显示与ComfyUI的连接状态（已连接/未连接）。
*   **双向通信**:
    *   **Blender -> ComfyUI**: 通过ZMQ发送渲染任务、元数据和图像二进制数据。
    *   **ComfyUI -> Blender**: 通过HTTP将处理完成的图像数据发送回Blender。
*   **全自动依赖管理**: 插件首次启用时，会自动通过Blender内置的Python环境安装所有必需的依赖库 (`sshtunnel`, `paramiko`, `pyzmq`, `msgspec`)，无需手动操作。
*   **后台任务处理**: 使用Blender的`bpy.app.timers`来稳定地处理来自ComfyUI的异步任务，不阻塞UI。
*   **健壮的错误处理**: 包含连接测试、超时和错误报告机制。

## 🚀 安装指南

### 前置要求

- **Blender**: 4.0 或更高版本
- **ComfyUI**: 运行中的服务器实例
- **网络**: 稳定的网络连接（用于依赖安装）

### 1. ComfyUI 节点

首先，确保您已经在ComfyUI中安装了兼容的接收节点。该节点需要能够处理来自Blender的多部分ZMQ消息。

**推荐节点**: 在 [ComfyUI-Manager](https://github.com/Comfy-Org/ComfyUI-Manager) 中搜索 "Blender Bridge" 或直接安装本插件配套的接收节点。

### 2. Blender 插件安装

#### 方法1：从 GitHub Releases 安装（推荐）

**步骤**：

1. **下载插件**
   - 访问 [Releases 页面](https://github.com/ageless-h/Blender-ComfyUI-Bridge/releases)
   - 下载最新版本的 `Blender-ComfyUI-Bridge-vX.X.zip` 文件
   - 例如：`Blender-ComfyUI-Bridge-v1.0.0.zip`

2. **在 Blender 中安装**
   ```
   Blender -> 编辑 -> 偏好设置 -> 插件
   ```

3. **安装文件**
   - 点击 `安装...` 按钮
   - 选择您刚刚下载的 `.zip` 文件
   - 等待安装完成

4. **启用插件**
   - 在插件列表中找到 "Blender-ComfyUI Bridge"
   - 勾选复选框以启用插件
   - 点击 `保存用户设置`

5. **自动依赖安装**
   - 插件首次启用时会自动检测并安装所需的依赖
   - 打开 `窗口 -> 切换系统控制台` 查看安装日志
   - 等待安装完成（可能需要几十秒到几分钟）
   - **重要**：安装完成后建议重启 Blender

#### 方法2：手动安装（高级用户）

1. **克隆仓库**
   ```bash
   git clone https://github.com/ageless-h/Blender-ComfyUI-Bridge.git
   cd Blender-ComfyUI-Bridge
   ```

2. **复制插件目录**
   - 将 `blender_addon` 目录复制到 Blender 的插件目录：
     ```
     # Windows
     C:\Users\YourName\AppData\Roaming\Blender Foundation\Blender\4.0\scripts\addons\

     # macOS
     /Users/YourName/Library/Application Support/Blender/4.0/scripts/addons/

     # Linux
     ~/.config/blender/4.0/scripts/addons/
     ```

3. **手动安装依赖**（如果自动安装失败）
   ```bash
   cd blender_addon
   pip install -r requirements.txt
   ```

### 3. 验证安装

1. 打开 Blender
2. 按 `N` 键打开侧边栏
3. 检查是否看到 `ComfyUI` 选项卡
4. 如果看到，安装成功！✅

## 🔧 使用方法

### 基础工作流

#### 第一步：打开 Blender 并找到插件面板

1. 在 Blender 的 3D 视图中，按 `N` 键打开侧边栏
2. 向下滚动找到 `ComfyUI` 选项卡

![面板位置示例](https://capsule-render.vercel.app/api?type=header&text=Blender+ComfyUI+Bridge&fontSize=24)

#### 第二步：配置连接

##### 直接连接模式

**适用场景**：ComfyUI 与 Blender 在同一台电脑或同一局域网

1. 在"连接设置"区域，取消勾选"启用 SSH 隧道"
2. 输入 ComfyUI 服务器的 ZMQ 地址
   - 本地默认：`127.0.0.1:5555`
   - 确认 ComfyUI 的 ZMQ 端口（通常在 5555）
3. 点击"测试连接"按钮
4. 等待状态变为"已连接"（绿色）

##### SSH 隧道模式

**适用场景**：ComfyUI 在远程服务器上

1. 勾选"启用 SSH 隧道"
2. 填写 SSH 服务器信息：
   - **主机**: `192.168.1.100`（示例 IP）
   - **端口**: `22`（默认 SSH 端口）
   - **用户名**: `your-username`
   - **密码**: 或选择**私钥**路径
3. **重要**：在"ComfyUI 服务器地址"中填写的地址是**相对于 SSH 服务器的**地址
   - 例如：如果 ComfyUI 在 SSH 服务器上运行，通常填写 `127.0.0.1:5555`
   - 如果 ComfyUI 在另一台机器，填写实际的 IP 地址，如 `192.168.1.200:5555`
4. 点击"建立 SSH 隧道"按钮
5. 等待隧道建立成功（状态显示"已连接"）

#### 第三步：选择结果接收

1. 在"结果接收"区域，点击文件夹图标
2. 选择一个 Blender 的图像数据块（Image Block）
3. 最好选择一个空的数据块，方便接收结果

#### 第四步：发送数据

**发送渲染结果**：

1. 选择"渲染结果"标签页
2. 选择图像格式：
   - **标准图像 (PNG/JPG)**：适合快速预览
   - **多通道 EXR**：包含所有渲染通道（Depth, Normal, AO 等）
3. 点击"渲染并发送"按钮
4. Blender 会渲染当前场景并将图像数据发送到 ComfyUI

**发送现有图像**：

1. 切换到"图像编辑器"标签页
2. 打开要发送的图像
3. 点击"发送当前图像"按钮
4. 图像会被发送到 ComfyUI

#### 第五步：接收结果

1. ComfyUI 处理完成后，结果会自动出现在你在第三步选择的图像数据块中
2. 你可以在 Blender 的图像编辑器中查看处理后的结果

## 💡 使用示例

### 示例1：本地渲染工作流

**场景**：在 Blender 中渲染一个角色，然后在 ComfyUI 中进行风格化处理。

```
Blender (本地)
├─ 渲染角色
├─ 发送渲染结果到 ComfyUI
├─ ComfyUI (本地网络)
│  ├─ 风格化处理
│  ├─ 生成风格化图像
│  └─ 返回结果到 Blender
└─ Blender 接收并显示结果
```

**效果**：快速迭代的本地 + AI 工作流，无需手动文件传输。

### 示例2：远程渲染工作流（SSH 隧道）

**场景**：在本地 Blender 中建模，在远程 ComfyUI 服务器上渲染，使用 SSH 隧道连接。

```
Blender (本地)
├─ 发送模型数据到 ComfyUI
├─ 通过 SSH 隧道连接
├─ ComfyUI (远程服务器)
│  ├─ 高质量渲染
│  ├─ 生成渲染结果
│  └─ 通过 HTTP 返回到 Blender
└─ Blender 接收并显示
```

**优势**：
- 利用远程服务器的强大 GPU
- 节省本地计算资源
- 支持跨平台工作

### 示例3：批量图像处理

**场景**：将 Blender 中渲染的多个不同场景发送到 ComfyUI 批量处理。

```
1. 场景1渲染 → 发送到 ComfyUI
2. 场景2渲染 → 发送到 ComfyUI
3. 场景3渲染 → 发送到 ComfyUI
4. ComfyUI 批量处理并返回所有结果
```

**工作流提示**：
- 可以在 Blender 中设置不同的输出数据块，方便接收不同场景的结果

## 📋 常见问题 (FAQ)

### Q1: 插件启用后没有看到侧边栏怎么办？

**A**: 按照以下步骤排查：
1. 确认插件已启用（编辑 → 插件 → 勾选）
2. 重启 Blender（完全关闭后重新打开）
3. 按 `N` 键打开侧边栏
4. 如果仍然看不到，检查 Blender 控制台是否有错误消息

### Q2: 连接测试失败，显示"未连接"

**A**: 检查以下项目：
1. **ComfyUI 是否运行中**？确保 ComfyUI 服务器正在运行
2. **ZMQ 端口是否正确**？默认是 `5555`，确认 ComfyUI 的 ZMQ 端口
3. **防火墙**？检查本地或远程服务器的防火墙是否阻止连接
4. **地址是否正确**？
   - 直接连接：`127.0.0.1:5555`
   - SSH 隧道：确保是相对于 SSH 服务器的地址
5. 尝试使用 ComfyUI 的 IP 地址而不是 `localhost`

### Q3: SSH 隧道建立失败

**A**: 常见问题和解决方案：
1. **私钥路径错误**：确保私钥文件存在且路径正确
2. **SSH 服务未运行**：确认 SSH 服务器上的 SSH 服务正在运行（端口 22）
3. **密码认证失败**：尝试使用 SSH 密钥认证，更安全
4. **网络问题**：尝试先 `ssh` 命令手动连接，确认 SSH 连接正常

### Q4: 图像发送后没有返回结果

**A**: 检查以下几点：
1. **ComfyUI 工作流是否正确配置**？确保接收节点在运行
2. **结果数据块是否选择**？确认在 Blender 中选择了接收数据的图像块
3. **查看 Blender 系统控制台**：检查是否有错误消息
4. **ComfyUI 是否有错误**？检查 ComfyUI 的日志/控制台输出

### Q5: 多通道 EXR 发送后看不到通道

**A**: 多通道 EXR 需要正确的接收节点：
1. 确保接收节点支持 `channel_map`
2. 使用支持的接收节点（通常会在节点描述中说明）
3. 检查 EXR 文件是否正确生成（可以先用 Blender 打开查看）

### Q6: 如何停止数据传输？

**A**: 目前插件在接收数据后不会自动停止，但可以：
1. 关闭 Blender 或重新打开场景
2. 停止 ComfyUI 工作流
3. SSH 隧道会自动断开（如果设置了超时）

## 🎬 视频教程（制作中）

> 📌 **提示**：详细的安装和使用视频教程正在制作中，敬请期待！

### 视频内容规划

1. **安装教程** - 从下载到首次使用的完整流程
2. **基础工作流演示** - 展示从 Blender 发送到 ComfyUI 的完整过程
3. **SSH 隧道配置** - 如何设置远程 ComfyUI 连接
4. **多通道 EXR 使用** - 如何利用多通道渲染数据
5. **故障排查指南** - 常见问题的解决方法

### 观看方式

- 视频将在 [YouTube](https://youtube.com/) 和 [Bilibili](https://www.bilibili.com/) 平台发布
- 视频链接将添加到此 README 的"视频教程"部分

### 为什么需要视频教程？

- 图文教程可能不够直观
- 实际操作演示更易于理解
- 涵盖更多使用场景和边缘情况

## 💻 技术实现细节 (供节点开发者参考)

本插件通过ZMQ的`REQ/REP`模式与ComfyUI节点通信，并采用**多部分消息 (Multipart Message)** 的格式发送数据。

### ZMQ 消息结构

节点接收到的ZMQ消息包含 **2** 个部分：

1.  **Part 1: 元数据 (Metadata)**
    *   **类型**: `msgspec` 编码的字典 (JSON)。
    *   **内容**: 包含操作指令和图像信息。

2.  **Part 2: 图像二进制数据 (Image Bytes)**
    *   **类型**: 原始字节流 (`bytes`)。
    *   **内容**: `.png` 或 `.exr` 文件的完整二进制内容。

**接收节点必须使用 `socket.recv_multipart()` 来正确解析这两个部分。**

### 元数据 (Metadata) 详解

元数据字典中包含以下关键字段：

*   `render_type` (字符串):
    *   `'standard'`: 表示第二部分数据是标准的 **PNG/JPG** 图像。
    *   `'multilayer_exr'`: 表示第二部分数据是多通道 **EXR** 图像。
    *   **接收节点必须根据此字段来决定处理逻辑。**

*   `channel_map` (字典):
    *   **仅在 `render_type` 为 `'multilayer_exr'` 时提供。**
    *   这是一个"翻译地图"，用于将ComfyUI期望的通道名 (key) 映射到EXR文件中实际的通道名 (value)。
    *   **示例**: `{'volume_direct': 'ViewLayer.VolumeDir', 'ambient_occlusion': 'ViewLayer.AO'}`。
    *   **接收节点在处理EXR时，必须使用此map来查找通道，而不是硬编码通道名。**

## 🤝 贡献指南

### 如何贡献？

我们欢迎各种形式的贡献！

#### 1. 报告 Bug 🐛

发现任何问题？请创建 [Issue](https://github.com/ageless-h/Blender-ComfyUI-Bridge/issues)：
- 详细描述问题
- 提供复现步骤
- 附上相关日志或截图
- 说明您的 Blender 和 ComfyUI 版本

#### 2. 提出新功能 💡

有新功能想法？请：
- 先在 [Discussions](https://github.com/ageless-h/Blender-ComfyUI-Bridge/discussions) 中讨论
- 确认功能需求和实现可行性
- 创建 Issue 跟踪开发进度

#### 3. 提交代码 PR 🔀

准备贡献代码？

1. **Fork** 本仓库
2
