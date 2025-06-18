import bpy

class BRIDGE_PT_MainPanel(bpy.types.Panel):
    bl_label = "ComfyUI Bridge"
    bl_idname = "BRIDGE_PT_MainPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ComfyBridge'

    def draw(self, context):
        layout = self.layout
        
        # 在受限上下文中，'scene' 可能不存在，必须先用 hasattr 检查
        if not hasattr(context, 'scene') or not context.scene:
            return
            
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
        
        # poll() 方法会自动处理按钮的可用状态，无需手动设置 active
        col.operator("bridge.render_and_send", text="渲染并发送到 ComfyUI", icon='RENDER_STILL')
        
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
        
        # 在受限上下文中，'scene' 可能不存在，必须先用 hasattr 检查
        if not hasattr(context, 'scene') or not context.scene:
            return
            
        props = context.scene.bridge_props

        col = layout.column()
        col.prop(props, "comfyui_address")
        col.prop(props, "blender_receiver_port")
        
        layout.separator()
        
        remote_box = layout.box()
        remote_box.label(text="远程工作流", icon='URL')
        remote_box.prop(props, "public_address_override")
        remote_box.label(text="需要公网IP和端口转发", icon='INFO')
