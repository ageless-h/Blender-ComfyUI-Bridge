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
