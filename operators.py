import bpy
import logging
import tempfile
import os

from .utils import comms, state

log = logging.getLogger(__name__)

class BRIDGE_OT_TestConnection(bpy.types.Operator):
    bl_idname = "bridge.test_connection"
    bl_label = "测试连接"
    bl_description = "向 ComfyUI 发送一个'ping'来测试连接状态"

    def execute(self, context):
        props = context.scene.bridge_props
        
        # 显示"正在连接..."状态
        props.connection_status = 'DISCONNECTED' # 先重置一下，这样用户能看到变化
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

        try:
            success = comms.send_ping(props.comfyui_address)
            if success:
                props.connection_status = 'CONNECTED'
                self.report({'INFO'}, "与 ComfyUI 连接成功！")
            else:
                props.connection_status = 'FAILED'
                self.report({'ERROR'}, "连接失败。请检查地址或确保ComfyUI服务器正在运行。")
        except Exception as e:
            props.connection_status = 'FAILED'
            self.report({'ERROR'}, f"发生未知错误: {e}")
            log.error(f"测试连接时发生错误: {e}", exc_info=True)
            
        return {'FINISHED'}

class BRIDGE_OT_RenderAndSend(bpy.types.Operator):
    bl_idname = "bridge.render_and_send"
    bl_label = "渲染并发送"
    bl_description = "渲染当前场景，并将结果和回传信息发送到 ComfyUI"
    
    @classmethod
    def poll(cls, context):
        # 在受限上下文中，'scene' 可能不存在，必须先用 hasattr 检查
        if not hasattr(context, 'scene') or not context.scene:
            return False
        
        props = context.scene.bridge_props
        return props.connection_status == 'CONNECTED' and props.target_image_datablock is not None

    def execute(self, context):
        props = context.scene.bridge_props
        
        # 1. 渲染并保存到临时文件
        try:
            # 使用临时目录来保存渲染结果
            render_dir = tempfile.gettempdir()
            # 从场景的渲染设置中获取文件格式和扩展名
            render_settings = context.scene.render
            file_format = render_settings.image_settings.file_format
            extension = ".png" # 默认值
            if file_format == 'PNG':
                extension = ".png"
            elif file_format == 'JPEG':
                extension = ".jpg"
            elif file_format == 'OPEN_EXR':
                extension = ".exr"
            # ...可以为其他格式添加更多 elif
            
            render_filename = f"blender_render_{os.getpid()}{extension}"
            render_path = os.path.join(render_dir, render_filename)
            render_settings.filepath = render_path
            
            log.info(f"正在渲染场景到: {render_path}...")
            bpy.ops.render.render(write_still=True)
            log.info(f"渲染完成，图像已保存到: {render_path}")

        except Exception as e:
            self.report({'ERROR'}, f"渲染失败: {e}")
            log.error(f"渲染操作失败: {e}", exc_info=True)
            return {'CANCELLED'}

        # 2. 智能构建回传地址
        if props.public_address_override:
            # 用户指定了公网地址
            blender_server_address = f"http://{props.public_address_override}:{props.blender_receiver_port}"
        else:
            # 自动检测或使用本地地址
            # 注意：这里的 127.0.0.1 仅在 ComfyUI 和 Blender 在同一台机器上时才有效
            blender_server_address = f"http://127.0.0.1:{props.blender_receiver_port}"

        # 3. 构建元数据
        metadata = {
            "type": "render_and_return",
            "render_path": render_path,
            "return_info": {
                "blender_server_address": blender_server_address,
                "image_datablock_name": props.target_image_datablock.name
            }
        }
        log.debug(f"构建的元数据: {metadata}")

        # 4. 发送数据
        success = comms.send_data(props.comfyui_address, metadata)
        if success:
            self.report({'INFO'}, "数据已成功发送到 ComfyUI。")
        else:
            self.report({'ERROR'}, "数据发送失败！请检查控制台日志。")
        
        return {'FINISHED'}
