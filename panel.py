import bpy

# 一个辅助函数，用于获取当前活动的图像编辑器中的图像
def get_active_image_from_editor(context):
    for area in context.screen.areas:
        if area.type == 'IMAGE_EDITOR':
            if area.spaces.active:
                return area.spaces.active.image
    return None

class BRIDGE_PT_MainPanel(bpy.types.Panel):
    bl_label = "ComfyUI Bridge"
    bl_idname = "BRIDGE_PT_MainPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ComfyUI'

    def draw(self, context):
        layout = self.layout
        props = context.scene.bridge_props

        # --- 连接状态 ---
        box = layout.box()
        row = box.row(align=True)
        row.label(text="连接状态:")
        
        status = props.connection_status
        if status == 'DISCONNECTED': row.label(text="未连接", icon='RADIOBUT_OFF')
        elif status == 'CONNECTED': row.label(text="已连接", icon='RADIOBUT_ON')
        elif status == 'FAILED': row.label(text="连接失败", icon='ERROR')
        
        box.operator("bridge.test_connection", text="测试连接", icon='FILE_REFRESH')

        # --- 发送逻辑 ---
        box = layout.box()
        box.label(text="数据发送", icon='EXPORT')
        box.prop(props, "source_mode", expand=True)

        is_ready_for_send = props.connection_status == 'CONNECTED' and props.target_image_datablock is not None

        if props.source_mode == 'RENDER':
            col = box.column(align=True)
            col.enabled = is_ready_for_send
            col.prop(props, "render_mode")
            col.operator("bridge.send_data", text="渲染并发送", icon='RENDER_STILL')
        
        elif props.source_mode == 'IMAGE_EDITOR':
            col = box.column(align=True)
            col.enabled = is_ready_for_send
            
            active_image = get_active_image_from_editor(context)
            if active_image:
                col.template_preview(active_image, show_buttons=False)
                col.label(text=f"当前: {active_image.name}")
            else:
                col.label(text="请在图像编辑器中选择图像", icon='INFO')
            
            op = col.operator("bridge.send_data", text="发送当前图像", icon='IMAGE_DATA')
            if not active_image:
                op.enabled = False

        # --- 接收设置 ---
        box = layout.box()
        box.label(text="结果接收", icon='IMPORT')
        box.prop(props, "target_image_datablock")
        
        # --- 提示信息 ---
        if not is_ready_for_send:
            warning_box = layout.box()
            warning_box.label(text="请先完成设置:", icon='ERROR')
            if props.connection_status != 'CONNECTED':
                warning_box.label(text="- 点击 '测试连接' 直至成功", icon='RIGHTARROW')
            if props.target_image_datablock is None:
                warning_box.label(text="- 在下方选择一个 '目标图像'", icon='RIGHTARROW')

        # --- 连接设置 (可折叠) ---
        settings_box = layout.box()
        row = settings_box.row()
        row.prop(props, "show_connection_settings",
                 icon="TRIA_DOWN" if props.show_connection_settings else "TRIA_RIGHT",
                 icon_only=True, emboss=False)
        row.label(text="连接设置")

        if props.show_connection_settings:
            settings_box.prop(props, "comfyui_address")
            settings_box.prop(props, "blender_receiver_port")
            settings_box.prop(props, "public_address_override")

        # --- SSH 设置 (可折叠) ---
        ssh_box = layout.box()
        row = ssh_box.row()
        row.prop(props, "show_ssh_settings",
                 icon="TRIA_DOWN" if props.show_ssh_settings else "TRIA_RIGHT",
                 icon_only=True, emboss=False)
        row.label(text="SSH 隧道设置")

        if props.show_ssh_settings:
            ssh_box.prop(props, "use_ssh")
            
            # 仅在使用SSH时才显示详细信息
            if props.use_ssh:
                col = ssh_box.column()
                col.enabled = True # 确保内部控件是可编辑的
                col.prop(props, "ssh_host")
                col.prop(props, "ssh_port")
                col.prop(props, "ssh_user")
                col.prop(props, "ssh_password")
                col.prop(props, "ssh_key_path")
                col.label(text="注意: 插件会自动处理端口转发。", icon='INFO')
                col.label(text="ComfyUI地址应设为远程服务器的地址(如127.0.0.1:5555)。", icon='INFO')
                col.label(text="Blender接收端口将自动在远程服务器上映射。", icon='INFO')

# --- 注册 ---
panel_classes = (
    BRIDGE_PT_MainPanel,
)

def register():
    # 确保辅助函数在 panel 模块中可用
    bpy.types.Scene.get_active_image_from_editor = get_active_image_from_editor
    for cls in panel_classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(panel_classes):
        bpy.utils.unregister_class(cls)
    if hasattr(bpy.types.Scene, 'get_active_image_from_editor'):
        del bpy.types.Scene.get_active_image_from_editor
