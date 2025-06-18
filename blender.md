# Blender 插件 `ComfyUI-BlenderBridge` 技术规格与开发文档

**版本:** 2.0 (技术实现版)
**目标:** 制定一份详尽的技术规格，指导开发一个健壮、高效且用户友好的 Blender 插件。该插件旨在实现 Blender 与 ComfyUI 之间可靠、高速、双向的数据流转，并能智能适应本地和远程网络环境。

---

## 第一部分：最终架构与文件结构

我们将采用经过验证的多文件包（Package）结构，以实现关注点分离和长期可维护性。

#### 1.1 文件结构

```
ComfyUI-BlenderBridge/
├── __init__.py              # 注册/注销, 启动/停止后台服务
├── blender_manifest.toml    # 插件元数据, 依赖项声明
├── properties.py            # PropertyGroup 数据模型定义
├── panel.py                 # UI 面板定义
├── operators.py             # 所有操作符 (用户动作) 定义
└── utils/
    ├── __init__.py
    ├── comms.py             # 封装 ZMQ 通信逻辑 (ping/data)
    ├── receiver.py          # 后台 HTTP 接收服务器
    └── state.py             # 全局共享状态 (任务队列, 线程引用)
```

---

## 第二部分：模块化实现细节

本部分将逐一拆解每个文件的核心职责与实现逻辑。

#### 2.1 `properties.py` - 数据模型

此文件定义了插件所有状态的唯一真实来源 (`Single Source of Truth`)。

```python
# properties.py
import bpy

class BridgeProperties(bpy.types.PropertyGroup):
    """插件的核心设置，将附加到场景中。"""

    # --- 连接设置 ---
    comfyui_address: bpy.props.StringProperty(
        name="ComfyUI 地址",
        description="ComfyUI ZMQ 服务器的地址",
        default="tcp://127.0.0.1:5555"
    )

    blender_receiver_port: bpy.props.IntProperty(
        name="Blender 接收端口",
        description="Blender 用于接收返回图像的端口",
        default=5556,
        min=1024,
        max=65535
    )

    public_address_override: bpy.props.StringProperty(
        name="公网地址覆盖",
        description="[远程] 输入您的公网IP或域名。需在路由器上设置端口转发"
    )

    # --- 状态管理 ---
    connection_status: bpy.props.EnumProperty(
        name="连接状态",
        items=[
            ('DISCONNECTED', '未连接', '尚未测试或连接'),
            ('CONNECTED', '已连接', '与ComfyUI的握手成功'),
            ('FAILED', '连接失败', '无法连接到ComfyUI'),
        ],
        default='DISCONNECTED'
    )

    # --- 核心功能 ---
    target_image_datablock: bpy.props.PointerProperty(
        name="目标图像",
        description="选择一个图像数据块，ComfyUI的结果将更新到此处",
        type=bpy.types.Image
    )
```

#### 2.2 `panel.py` - 用户界面

此文件负责将 `properties.py` 中定义的数据模型以用户友好的方式呈现出来。

```python
# panel.py
import bpy

class BRIDGE_PT_MainPanel(bpy.types.Panel):
    bl_label = "ComfyUI Bridge"
    bl_idname = "BRIDGE_PT_MainPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ComfyBridge'

    def draw(self, context):
        layout = self.layout
        props = context.scene.bridge_props # 获取数据模型

        # 状态指示器
        status_row = layout.row(align=True)
        if props.connection_status == 'CONNECTED':
            status_row.label(text="状态: 已连接", icon='CHECKMARK')
        elif props.connection_status == 'FAILED':
            status_row.label(text="状态: 连接失败", icon='ERROR')
        else:
            status_row.label(text="状态: 未连接", icon='QUESTION')
        
        status_row.operator("bridge.test_connection", text="", icon='FILE_REFRESH')

        # 核心功能区 (根据连接状态决定是否可用)
        main_box = layout.box()
        col = main_box.column()
        
        is_ready = (props.connection_status == 'CONNECTED' and props.target_image_datablock is not None)
        
        col.label(text="目标图像:")
        col.template_ID(props, "target_image_datablock", new="image.new", open="image.open")
        
        render_op = col.operator("bridge.render_and_send", text="渲染并发送到 ComfyUI", icon='RENDER_STILL')
        render_op.active = is_ready # 仅在连接且选定图像后可用
        
        if not is_ready:
            warning_col = col.column(align=True)
            warning_col.scale_y = 0.8
            if props.connection_status != 'CONNECTED':
                warning_col.label(text="请先成功测试连接", icon='INFO')
            if props.target_image_datablock is None:
                warning_col.label(text="请选择或创建一个目标图像", icon='INFO')


class BRIDGE_PT_ConnectionSettingsPanel(bpy.types.Panel):
    bl_label = "连接设置"
    bl_idname = "BRIDGE_PT_ConnectionSettingsPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ComfyBridge'
    bl_parent_id = 'BRIDGE_PT_MainPanel' # 作为主面板的子面板
    bl_options = {'DEFAULT_CLOSED'} # 默认折叠

    def draw(self, context):
        layout = self.layout
        props = context.scene.bridge_props

        col = layout.column()
        col.prop(props, "comfyui_address")
        col.prop(props, "blender_receiver_port")
        
        layout.separator()
        
        remote_box = layout.box()
        remote_box.label(text="远程工作流", icon='URL')
        remote_box.prop(props, "public_address_override")
        remote_box.label(text="需要公网IP和端口转发", icon='INFO')
```

#### 2.3 `operators.py` - 用户动作

此文件定义了用户通过UI触发的所有后端逻辑。

```python
# operators.py
import bpy
# ... (其他导入)

class BRIDGE_OT_TestConnection(bpy.types.Operator):
    bl_idname = "bridge.test_connection"
    bl_label = "测试连接"
    bl_description = "向 ComfyUI 发送一个'ping'来测试连接状态"

    def execute(self, context):
        props = context.scene.bridge_props
        # 伪代码:
        # success = utils.comms.send_ping(props.comfyui_address)
        # if success:
        #     props.connection_status = 'CONNECTED'
        #     self.report({'INFO'}, "与 ComfyUI 连接成功！")
        # else:
        #     props.connection_status = 'FAILED'
        #     self.report({'ERROR'}, "连接失败。请检查地址或ComfyUI是否运行。")
        return {'FINISHED'}

class BRIDGE_OT_RenderAndSend(bpy.types.Operator):
    bl_idname = "bridge.render_and_send"
    bl_label = "渲染并发送"
    bl_description = "渲染当前场景，并将结果和回传信息发送到 ComfyUI"
    
    @classmethod
    def poll(cls, context):
        # 使用 poll 方法确保在按钮不可用时操作符本身也被禁用
        props = context.scene.bridge_props
        return props.connection_status == 'CONNECTED' and props.target_image_datablock is not None

    def execute(self, context):
        props = context.scene.bridge_props
        
        # 1. 渲染并获取路径
        # ... bpy.ops.render.render() ...
        # render_path = ...
        
        # 2. 智能构建回传地址
        # if props.public_address_override:
        #     blender_server_address = f"http://{props.public_address_override}:{props.blender_receiver_port}"
        # else:
        #     blender_server_address = f"http://127.0.0.1:{props.blender_receiver_port}"

        # 3. 构建元数据
        # metadata = {
        #     "type": "render_and_return",
        #     "render_path": render_path,
        #     "return_info": {
        #         "blender_server_address": blender_server_address,
        #         "image_datablock_name": props.target_image_datablock.name
        #     }
        # }

        # 4. 发送数据
        # success = utils.comms.send_data(props.comfyui_address, metadata)
        # if success:
        #     self.report({'INFO'}, "数据已成功发送到 ComfyUI。")
        # else:
        #     self.report({'ERROR'}, "数据发送失败！")
        
        return {'FINISHED'}

class BRIDGE_OT_QueueMonitor(bpy.types.Operator):
    """一个不可见的、在后台运行的模态操作符，用于安全地处理任务队列。"""
    bl_idname = "bridge.queue_monitor"
    bl_label = "队列监视器"

    _timer = None

    def modal(self, context, event):
        if event.type == 'TIMER':
            # 伪代码:
            # from utils.state import task_queue
            # if not task_queue.empty():
            #     path, image_name = task_queue.get()
            #     
            #     # 在主线程安全地更新 Blender 数据
            #     image = bpy.data.images.get(image_name)
            #     if not image:
            #         # 如果需要，可以创建新图像
            #         image = bpy.data.images.new(image_name, width=1, height=1)
            #     
            #     image.filepath = path
            #     image.reload()
            #     print(f"图像 '{image_name}' 已更新。")

        return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.5, window=context.window) # 每 0.5 秒检查一次
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
```

#### 2.4 `utils` - 工具与服务

##### `utils/comms.py`
封装所有与 ComfyUI 的 ZMQ 通信。
```python
# utils/comms.py
import zmq
import msgspec

def send_ping(address):
    # ... 创建 ZMQ REQ socket ...
    # ... 设置超时 (socket.setsockopt) ...
    # ... socket.connect(address) ...
    # ... socket.send(msgspec.msgpack.encode({"type": "ping"})) ...
    # ... 使用 socket.poll() 等待回复 ...
    # ... 如果收到 "pong"，返回 True，否则 False ...
    # ... 确保 socket.close() ...

def send_data(address, metadata):
    # 逻辑与 send_ping 类似，但发送的是包含完整元数据的消息
    # ...
```

##### `utils/receiver.py`
在后台线程中运行的 HTTP 服务器，用于接收 ComfyUI 的返回结果。
```python
# utils/receiver.py
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
# from utils.state import task_queue

class ReceiverRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 伪代码：
        # content_type = self.headers['Content-Type']
        # if 'application/json' in content_type:
        #     # 本地模式
        #     # 读取请求体, json.loads()
        #     # path = data['image_path']
        #     # task_queue.put((path, image_name))
        # else:
        #     # 远程模式 (e.g., image/png)
        #     # 读取二进制请求体
        #     # 将其保存到临时文件, get temp_path
        #     # task_queue.put((temp_path, image_name))
        #
        # self.send_response(200)
        # self.end_headers()
        # self.wfile.write(b'OK')

class HttpReceiver(threading.Thread):
    def run(self):
        # ... 设置并启动 HTTPServer ...
    def stop(self):
        # ... 安全地关闭服务器 ...
```

##### `utils/state.py`
定义所有需要跨模块、跨线程共享的状态。
```python
# utils/state.py
import queue

# 用于从 HTTP 接收线程向 Blender 主线程传递任务的队列
task_queue = queue.Queue()

# 用于持有后台线程的引用，以便在插件卸载时能安全地停止它
receiver_thread = None
```

#### 2.5 `__init__.py` - 插件生命周期管理

这是插件的入口和出口，负责注册所有组件并管理后台服务的生命周期。
```python
# __init__.py
bl_info = { ... }

# ... 导入所有类 ...
from . import properties
from . import panel
# ...

classes = ( ... ) # 包含所有要注册的 Panel, Operator, PropertyGroup 类

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # 将 PropertyGroup 附加到 Scene
    bpy.types.Scene.bridge_props = bpy.props.PointerProperty(type=properties.BridgeProperties)

    # 伪代码:
    # 启动后台服务
    # utils.state.receiver_thread = utils.receiver.HttpReceiver()
    # utils.state.receiver_thread.start()
    
    # 启动队列监视器
    # bpy.ops.bridge.queue_monitor('INVOKE_DEFAULT')

def unregister():
    # 伪代码:
    # 停止后台服务
    # if utils.state.receiver_thread:
    #     utils.state.receiver_thread.stop()
    
    # 删除 PropertyGroup
    del bpy.types.Scene.bridge_props

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

```

---

## 第三部分：依赖与打包

-   **依赖管理:** 采用官方推荐的"捆绑 Wheels"策略。将 `pyzmq` 和 `msgspec` 的 `.whl` 文件放入 `wheels/` 子目录，并在 `blender_manifest.toml` 中声明。
-   **打包:** 将整个 `ComfyUI-BlenderBridge` 文件夹打包为 `.zip` 文件进行分发。

这份文档提供了从数据模型、UI、用户操作到后台服务的完整实现蓝图，是后续编码工作的坚实基础。

---

## 第四部分：故障排除

### 错误: `No module named 'zmq'` 或 `No module named 'msgspec'`

在某些系统环境下，Blender 的自动依赖安装机制 (`wheels_path`) 可能无法正常工作。如果您在启用插件时遇到此错误，请按照以下步骤手动安装依赖项：

1.  **找到 Blender 的 Python 解释器路径:**
    *   打开 Blender。
    *   切换到顶部的 `Scripting` 工作区。
    *   在下方的"Python 控制台"中，输入以下两行代码，然后按回车：
        ```python
        import sys
        print(sys.executable)
        ```
    *   控制台将打印出一个文件路径。请复制此路径，它看起来类似于：`C:\Program Files\Blender Foundation\Blender 4.3\4.3\python\bin\python.exe`。

2.  **打开系统终端:**
    *   在 Windows 上，打开 **CMD (命令提示符)** 或 **PowerShell**。
    *   在 macOS 或 Linux 上，打开**终端 (Terminal)**。

3.  **手动安装依赖:**
    *   在终端中，使用您刚刚复制的 Blender Python 路径，并结合插件的 `wheels` 目录路径，来执行 `pip install` 命令。
    *   **请务必将以下命令中的 `[您的Blender Python路径]` 和 `[插件的绝对路径]` 替换为您系统上的真实路径。**

    **Windows 示例:**
    ```powershell
    # 安装 pyzmq
    & "[您的Blender Python路径]" -m pip install "[插件的绝对路径]\wheels\pyzmq-27.0.0-cp311-cp311-win_amd64.whl"

    # 安装 msgspec
    & "[您的Blender Python路径]" -m pip install "[插件的绝对路径]\wheels\msgspec-0.19.0-cp311-cp311-win_amd64.whl"
    ```

    **macOS / Linux 示例:**
    ```bash
    # 安装 pyzmq (示例路径，请替换)
    /path/to/blender/python -m pip install /path/to/plugin/wheels/pyzmq-27.0.0-cp311-cp311-manylinux_2_28_x86_64.whl

    # 安装 msgspec (示例路径，请替换)
    /path/to/blender/python -m pip install /path/to/plugin/wheels/msgspec-0.19.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
    ```

4.  **重启 Blender:**
    *   完成两条安装命令后，重启 Blender。插件现在应该能够正常启用。 