import bpy
import logging
import tempfile
import os

from .utils import comms
from .panel import get_active_image_from_editor # 确保从 panel 导入

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

class BRIDGE_OT_SendData(bpy.types.Operator):
    bl_idname = "bridge.send_data"
    bl_label = "发送数据到 ComfyUI"
    bl_description = "根据所选模式，发送数据到 ComfyUI"
    
    @classmethod
    def poll(cls, context):
        if not hasattr(context, 'scene') or not context.scene:
            return False
        
        props = context.scene.bridge_props
        if props.connection_status != 'CONNECTED' or not props.target_image_datablock:
            return False
            
        if props.source_mode == 'IMAGE_EDITOR':
            return get_active_image_from_editor(context) is not None
            
        return True

    def _build_channel_map(self, view_layer):
        """
        根据EXR文件内容的直接证据，构建从ComfyUI期望名到EXR实际通道名的映射。
        这是最终的、基于证据的实现。
        """
        channel_map = {}
        
        # 关键：从活动的视图层动态获取名称作为前缀
        prefix = view_layer.name

        # 这个映射表基于对EXR文件的分析进行了最终修正
        PASS_MAP = {
            'use_pass_combined': ('combined', 'Combined'),
            'use_pass_z': ('depth', 'Depth'),
            'use_pass_mist': ('mist', 'Mist'),
            'use_pass_normal': ('normal', 'Normal'),
            'use_pass_vector': ('vector', 'Vector'),
            'use_pass_shadow': ('shadow', 'Shadow'),
            'use_pass_ambient_occlusion': ('ambient_occlusion', 'AO'),
            'use_pass_emit': ('emission', 'Emit'),
            'use_pass_environment': ('environment', 'Env'),
            'use_pass_diffuse_direct': ('diffuse_direct', 'DiffDir'),
            'use_pass_diffuse_color': ('diffuse_color', 'DiffCol'),
            'use_pass_glossy_direct': ('glossy_direct', 'GlossDir'),
            'use_pass_glossy_color': ('glossy_color', 'GlossCol'),
            'use_pass_transmission_direct': ('transmission_direct', 'TransDir'),
            'use_pass_transmission_color': ('transmission_color', 'Transp'), # 修正: 根据文件分析，应为 Transp
            'use_pass_position': ('position', 'Position'),
            'use_pass_volume_direct': ('volume_direct', 'VolumeDir'),       # 修正: 根据文件分析，应为 VolumeDir
        }

        # 遍历所有已知的标准渲染通道
        for prop_name, (comfy_name, exr_base_name) in PASS_MAP.items():
            if getattr(view_layer, prop_name, False):
                # 构建完整的EXR通道基础名称 (例如 "ViewLayer.AO")
                full_exr_name = f"{prefix}.{exr_base_name}"
                channel_map[comfy_name] = full_exr_name

        # 单独处理自定义AOV (它们同样会获得前缀)
        for aov in view_layer.aovs:
            if aov.is_active:
                comfy_name = aov.name.lower().replace(' ', '_')
                full_exr_name = f"{prefix}.{aov.name}"
                channel_map[comfy_name] = full_exr_name

        log.info(f"构建的最终通道映射表 (带前缀): {channel_map}")
        return channel_map

    def execute(self, context):
        props = context.scene.bridge_props
        
        # 根据模式执行不同逻辑
        if props.source_mode == 'RENDER':
            return self.execute_render(context)
        elif props.source_mode == 'IMAGE_EDITOR':
            return self.execute_send_image(context)
            
        return {'CANCELLED'}

    def execute_render(self, context):
        props = context.scene.bridge_props
        scene = context.scene
        render_settings = scene.render
        
        # 保存用户原始设置
        original_filepath = render_settings.filepath
        original_format = render_settings.image_settings.file_format
        original_color_depth = render_settings.image_settings.color_depth

        try:
            render_dir = tempfile.gettempdir()
            render_filename_base = f"blender_render_{os.getpid()}"
            metadata = {}

            if props.render_mode == 'MULTILAYER_EXR':
                render_settings.image_settings.file_format = 'OPEN_EXR_MULTILAYER'
                render_settings.image_settings.color_depth = '32'
                extension = ".exr"
                metadata["render_type"] = "multilayer_exr"
                
                # --- 构建并添加最终的通道映射表 ---
                active_view_layer = context.view_layer
                channel_map = self._build_channel_map(active_view_layer)
                if channel_map:
                    metadata["channel_map"] = channel_map

            else: # STANDARD
                file_format = render_settings.image_settings.file_format
                extension = ".png" # 默认
                if file_format == 'PNG': extension = ".png"
                elif file_format == 'JPEG': extension = ".jpg"
                metadata["render_type"] = "standard"

            render_filename = f"{render_filename_base}{extension}"
            render_path = os.path.join(render_dir, render_filename)
            render_settings.filepath = render_path
            
            log.info(f"正在渲染场景到: {render_path}...")
            bpy.ops.render.render(write_still=True)
            log.info("渲染完成。")

        except Exception as e:
            self.report({'ERROR'}, f"渲染失败: {e}")
            log.error(f"渲染操作失败: {e}", exc_info=True)
            return {'CANCELLED'}
        finally:
            # 恢复用户设置
            render_settings.filepath = original_filepath
            render_settings.image_settings.file_format = original_format
            render_settings.image_settings.color_depth = original_color_depth
            log.info("用户原始渲染设置已恢复。")

        return self.send_to_comfyui(context, render_path, metadata)

    def execute_send_image(self, context):
        image = get_active_image_from_editor(context)
        if not image:
            self.report({'ERROR'}, "在图像编辑器中没有找到活动的图像。")
            return {'CANCELLED'}

        temp_dir = tempfile.gettempdir()
        image_path = ""
        
        # 如果图像有源文件路径，直接使用
        if image.source == 'FILE' and image.filepath:
            # os.path.abspath is needed for relative paths
            image_path = os.path.abspath(bpy.path.abspath(image.filepath))
            log.info(f"直接使用图像源文件: {image_path}")
        # 如果是打包或生成的图像，则保存到临时文件
        else:
            try:
                # Blender 无法直接保存为 jpg，所以我们统一存为 png
                filename = f"blender_image_{image.name.replace(' ', '_')}_{os.getpid()}.png"
                temp_path = os.path.join(temp_dir, filename)
                
                # 保存前需要确保图像不是脏的（比如有未应用的 viewer node 更改）
                if image.is_dirty:
                    image.update()

                # 使用 save_render 将图像（可能是 viewer node 的结果）保存
                image.save_render(filepath=temp_path, scene=context.scene)
                image_path = temp_path
                log.info(f"图像 '{image.name}' 已临时保存到: {image_path}")
            except Exception as e:
                self.report({'ERROR'}, f"保存图像失败: {e}")
                log.error(f"保存图像 '{image.name}' 失败: {e}", exc_info=True)
                return {'CANCELLED'}
        
        metadata = {"render_type": "direct_image"}
        return self.send_to_comfyui(context, image_path, metadata)


    def send_to_comfyui(self, context, file_path, user_metadata={}):
        props = context.scene.bridge_props
        image_data = None
        
        # 1. 读取文件内容到内存
        try:
            with open(file_path, 'rb') as f:
                image_data = f.read()
            log.info(f"成功读取文件 '{os.path.basename(file_path)}' ({len(image_data)} bytes).")
        except Exception as e:
            self.report({'ERROR'}, f"读取文件失败: {file_path}. 原因: {e}")
            log.error(f"读取文件 '{file_path}' 失败: {e}", exc_info=True)
            return {'CANCELLED'}

        # 2. 构建元数据
        if props.public_address_override:
            blender_server_address = f"http://{props.public_address_override}:{props.blender_receiver_port}"
        else:
            blender_server_address = f"http://127.0.0.1:{props.blender_receiver_port}"

        metadata = {
            "type": "render_and_return",
            "filename": os.path.basename(file_path), # 发送文件名而不是完整路径
            "return_info": {
                "blender_server_address": blender_server_address,
                "image_datablock_name": props.target_image_datablock.name
            }
        }
        metadata.update(user_metadata)
        
        # 3. 发送数据
        log.debug(f"构建的元数据: {metadata}")
        success = comms.send_data(props.comfyui_address, metadata, image_data)
        if success:
            self.report({'INFO'}, "数据已成功发送到 ComfyUI。")
        else:
            self.report({'ERROR'}, "数据发送失败！请检查控制台日志。")
            # 注意：即使发送失败，临时文件也应该被清理
        
        # 4. 清理临时文件
        # 我们只清理在 temp 目录中由插件自己创建的文件
        if tempfile.gettempdir() in os.path.abspath(file_path):
            try:
                os.remove(file_path)
                log.info(f"已删除临时文件: {file_path}")
            except Exception as e:
                log.warning(f"删除临时文件失败 '{file_path}': {e}")

        return {'FINISHED'}
