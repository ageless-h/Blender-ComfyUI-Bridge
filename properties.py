import bpy
from .utils import state

def port_update_callback(self, context):
    """当用户在UI上修改端口号时，此函数被调用"""
    # 'self' 是属性组 (BridgeProperties) 的实例
    new_port = self.blender_receiver_port
    # 使用 state 模块中的函数来安全地重启服务器
    state.start_receiver_server(new_port)
    return None

class BridgeProperties(bpy.types.PropertyGroup):
    """插件的核心设置，将附加到场景中。"""

    # --- 连接设置 ---
    comfyui_address: bpy.props.StringProperty(
        name="ComfyUI 服务器地址",
        description="ComfyUI 服务器的地址 (例如: 127.0.0.1:5555)",
        default="127.0.0.1:5555",
    )

    blender_receiver_port: bpy.props.IntProperty(
        name="Blender 接收端口",
        description="Blender 用于接收返回图像的端口",
        default=5556,
        min=1024,
        max=65535,
        update=port_update_callback,
    )

    public_address_override: bpy.props.StringProperty(
        name="公网/覆盖地址",
        description="如果 Blender 和 ComfyUI 不在同一台机器或 Docker 网络中，请在此处指定 Blender 所在机器可被 ComfyUI 访问到的地址（不含端口）",
        default="",
    )

    # --- 新增: SSH 隧道设置 ---
    show_ssh_settings: bpy.props.BoolProperty(
        name="显示SSH设置",
        description="展开或折叠SSH隧道设置",
        default=False
    )

    use_ssh: bpy.props.BoolProperty(
        name="使用SSH隧道",
        description="通过SSH隧道安全地连接到远程ComfyUI服务器",
        default=False
    )

    ssh_host: bpy.props.StringProperty(
        name="SSH 主机",
        description="SSH服务器的地址或主机名",
        default=""
    )

    ssh_port: bpy.props.StringProperty(
        name="SSH 端口",
        description="SSH服务的端口号 (例如: 22)",
        default="",
    )

    ssh_user: bpy.props.StringProperty(
        name="SSH 用户名",
        description="登录SSH服务器的用户名",
        default="root"
    )

    ssh_password: bpy.props.StringProperty(
        name="SSH 密码/私钥密码",
        description="SSH密码或私钥的密码。如果使用私钥且私钥无密码，可留空",
        default="",
        subtype='PASSWORD'
    )

    ssh_key_path: bpy.props.StringProperty(
        name="SSH 私钥文件路径",
        description="（可选）使用私钥文件进行认证。如果提供，将优先于密码认证",
        default="",
        subtype='FILE_PATH'
    )

    # --- 状态管理 ---
    connection_status: bpy.props.EnumProperty(
        name="连接状态",
        items=[
            ('DISCONNECTED', "未连接", "尚未建立连接"),
            ('CONNECTED', "已连接", "成功连接到服务器"),
            ('FAILED', "失败", "连接尝试失败"),
        ],
        default='DISCONNECTED'
    )

    show_connection_settings: bpy.props.BoolProperty(
        name="显示连接设置",
        description="展开或折叠连接设置",
        default=False
    )

    # --- 核心功能 ---
    target_image_datablock: bpy.props.PointerProperty(
        name="目标图像数据块",
        description="选择一个图像数据块，用于接收和显示从 ComfyUI 返回的结果",
        type=bpy.types.Image
    )

    source_mode: bpy.props.EnumProperty(
        name="数据源",
        description="选择要发送到 ComfyUI 的数据来源",
        items=[
            ('RENDER', "渲染结果", "渲染当前场景并发送"),
            ('IMAGE_EDITOR', "图像编辑器", "直接发送来自图像编辑器的图像"),
        ],
        default='RENDER',
    )

    render_mode: bpy.props.EnumProperty(
        name="渲染模式",
        description="选择渲染输出的格式",
        items=[
            ('STANDARD', "标准图像 (PNG/JPG)", "使用场景设置的标准格式渲染"),
            ('MULTILAYER_EXR', "多通道 EXR", "将所有启用的渲染通道打包到一个 EXR 文件中"),
        ],
        default='STANDARD',
    )
