import bpy
import logging
import tempfile
import os
import time

from .utils import comms, tunnel, state
from .panel import get_active_image_from_editor

log = logging.getLogger(__name__)

def _ensure_ssh_tunnel(props):
    """
    检查是否需要SSH隧道，并确保它正在运行。
    返回一个元组 (success, error_message)。
    """
    if not props.use_ssh:
        return True, None

    if not props.ssh_port:
        return False, "Please specify a valid port in SSH settings."

    try:
        port = int(props.ssh_port)
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        return False, f"Invalid SSH port: '{props.ssh_port}'. Please enter a number between 1-65535."

    manager = tunnel.get_tunnel_manager(props)
    if not manager:
        msg = "Cannot create SSH tunnel manager."
        log.error(msg)
        return False, msg
        
    status, error_msg = tunnel.get_tunnel_status()

    if status == "ACTIVE":
        return True, None
    
    if status == "ERROR":
        log.error(f"SSH隧道处于错误状态: {error_msg}")
        tunnel.stop_tunnel()
        manager = tunnel.get_tunnel_manager(props)

    log.info("正在启动SSH隧道...")
    manager.start()
    
    for _ in range(100):
        time.sleep(0.1)
        status, error_msg = tunnel.get_tunnel_status()
        if status == "ACTIVE":
            log.info("SSH隧道成功启动。")
            return True, None
        if status == "ERROR":
            msg = f"SSH tunnel start failed: {error_msg}"
            log.error(msg)
            return False, msg
            
    msg = "SSH tunnel start timeout."
    log.error(msg)
    return False, msg

def _get_comfyui_address(props):
    """根据是否使用SSH隧道，获取正确的ComfyUI ZMQ地址。"""
    if props.use_ssh:
        # 如果使用隧道，ZMQ客户端总是连接到本地转发的端口
        try:
            _, remote_port_str = props.comfyui_address.split(':')
            return f"127.0.0.1:{remote_port_str}"
        except ValueError:
            # 如果comfyui_address格式不正确，返回一个明显错误的值
            return "0.0.0.0:0"
    else:
        return props.comfyui_address
        
def _get_blender_callback_address(props):
    """
    根据是否使用SSH隧道和用户设置，获取正确的Blender回调HTTP地址。
    这个地址是发送给ComfyUI的，告诉它处理完后应该把图片发到哪里。
    """
    if props.use_ssh:
        # 如果使用隧道，ComfyUI需要连接到远程服务器上由SSH创建的监听端口
        # 这个端口会将流量转发回本地Blender
        return f"http://127.0.0.1:{props.blender_receiver_port}"

    if props.public_address_override:
        return f"http://{props.public_address_override}:{props.blender_receiver_port}"
    
    # 默认情况，ComfyUI和Blender在同一网络
    # 注意：这里我们假设ComfyUI可以访问到Blender的'localhost'或'127.0.0.1'
    # 如果在docker等复杂网络中，用户需要使用 public_address_override
    return f"http://127.0.0.1:{props.blender_receiver_port}"

class BRIDGE_OT_TestConnection(bpy.types.Operator):
    """向ComfyUI发送一个'ping'来测试连接状态"""
    bl_idname = "bridge.test_connection"
    bl_label = "测试连接"
    bl_description = "向 ComfyUI 发送一个'ping'来测试连接状态"

    def execute(self, context):
        props = context.scene.bridge_props
        
        success, msg = _ensure_ssh_tunnel(props)
        if not success:
            self.report({'OPERATOR'}, f"[ERROR] {msg}")
            log.error(msg)
            props.connection_status = 'FAILED'
            return {'FINISHED'}

        target_address = _get_comfyui_address(props)
        log.info(f"正在尝试连接到: {target_address}")

        props.connection_status = 'DISCONNECTED'
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

        try:
            success = comms.send_ping(target_address)
            if success:
                props.connection_status = 'CONNECTED'
                msg = "Successfully connected to ComfyUI!"
                self.report({'OPERATOR'}, f"[INFO] {msg}")
                log.info("与 ComfyUI 连接成功！")
            else:
                props.connection_status = 'FAILED'
                msg = "Connection failed. Please check the address or ensure ComfyUI is running."
                self.report({'OPERATOR'}, f"[ERROR] {msg}")
                log.error("连接失败。请检查地址或确保ComfyUI服务器正在运行。")
        except Exception as e:
            props.connection_status = 'FAILED'
            msg = f"An unknown error occurred: {e}"
            self.report({'OPERATOR'}, f"[ERROR] {msg}")
            log.error(f"发生未知错误: {e}", exc_info=True)
            
        return {'FINISHED'}

class BRIDGE_OT_SendData(bpy.types.Operator):
    """根据所选模式，发送数据到ComfyUI"""
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
        """根据当前视图层的设置，构建通道映射表。"""
        channel_map = {}
        prefix = view_layer.name

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
            'use_pass_transmission_color': ('transmission_color', 'Transp'),
            'use_pass_position': ('position', 'Position'),
            'use_pass_volume_direct': ('volume_direct', 'VolumeDir'),
        }

        for prop_name, (comfy_name, exr_base_name) in PASS_MAP.items():
            if getattr(view_layer, prop_name, False):
                full_exr_name = f"{prefix}.{exr_base_name}"
                channel_map[comfy_name] = full_exr_name

        for aov in view_layer.aovs:
            if aov.is_active:
                comfy_name = aov.name.lower().replace(' ', '_')
                full_exr_name = f"{prefix}.{aov.name}"
                channel_map[comfy_name] = full_exr_name

        log.info(f"构建的最终通道映射表 (带前缀): {channel_map}")
        return channel_map

    def execute(self, context):
        props = context.scene.bridge_props
        state.start_receiver_server(props.blender_receiver_port)
        if props.source_mode == 'RENDER':
            return self.execute_render(context)
        elif props.source_mode == 'IMAGE_EDITOR':
            return self.execute_send_image(context)
        return {'CANCELLED'}

    def execute_render(self, context):
        props = context.scene.bridge_props
        scene = context.scene
        render_settings = scene.render
        
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
                
                active_view_layer = context.view_layer
                channel_map = self._build_channel_map(active_view_layer)
                if channel_map:
                    metadata["channel_map"] = channel_map

            else: # STANDARD
                file_format = render_settings.image_settings.file_format
                extension = ".jpg" if file_format == 'JPEG' else ".png"
                metadata["render_type"] = "standard"

            render_filename = f"{render_filename_base}{extension}"
            render_path = os.path.join(render_dir, render_filename)
            render_settings.filepath = render_path
            
            log.info(f"正在渲染场景到: {render_path}...")
            bpy.ops.render.render(write_still=True)
            log.info("渲染完成。")

        except Exception as e:
            msg = f"Render failed: {e}"
            self.report({'OPERATOR'}, f"[ERROR] {msg}")
            log.error(f"渲染操作失败: {e}", exc_info=True)
            return {'CANCELLED'}
        finally:
            render_settings.filepath = original_filepath
            render_settings.image_settings.file_format = original_format
            render_settings.image_settings.color_depth = original_color_depth
            log.info("用户原始渲染设置已恢复。")

        return self.send_to_comfyui(context, render_path, metadata)

    def execute_send_image(self, context):
        image = get_active_image_from_editor(context)
        if not image:
            msg = "No active image found in the Image Editor."
            self.report({'OPERATOR'}, f"[ERROR] {msg}")
            log.error("在图像编辑器中没有找到活动的图像。")
            return {'CANCELLED'}

        temp_dir = tempfile.gettempdir()
        image_path = ""
        
        if image.source == 'FILE' and image.filepath:
            image_path = os.path.abspath(bpy.path.abspath(image.filepath))
        else:
            try:
                filename = f"blender_image_{image.name.replace(' ', '_')}_{os.getpid()}.png"
                temp_path = os.path.join(temp_dir, filename)
                
                if image.is_dirty:
                    image.update()

                image.save_render(filepath=temp_path, scene=context.scene)
                image_path = temp_path
                log.info(f"图像 '{image.name}' 已临时保存到: {image_path}")
            except Exception as e:
                msg = f"Failed to save image: {e}"
                self.report({'OPERATOR'}, f"[ERROR] {msg}")
                log.error(f"保存图像 '{image.name}' 失败: {e}", exc_info=True)
                return {'CANCELLED'}
        
        return self.send_to_comfyui(context, image_path, {"render_type": "direct_image"})

    def send_to_comfyui(self, context, file_path, user_metadata=None):
        props = context.scene.bridge_props
        image_data = None
        
        success, msg = _ensure_ssh_tunnel(props)
        if not success:
            self.report({'OPERATOR'}, f"[ERROR] {msg}")
            log.error(msg)
            return {'CANCELLED'}

        try:
            with open(file_path, 'rb') as f:
                image_data = f.read()
        except Exception as e:
            msg = f"Failed to read file: {file_path}. Reason: {e}"
            self.report({'OPERATOR'}, f"[ERROR] {msg}")
            log.error(f"读取文件 '{file_path}' 失败: {e}", exc_info=True)
            return {'CANCELLED'}

        blender_server_address = _get_blender_callback_address(props)
        metadata = {
            "type": "render_and_return",
            "filename": os.path.basename(file_path),
            "return_info": {
                "blender_server_address": blender_server_address,
                "image_datablock_name": props.target_image_datablock.name
            }
        }
        if user_metadata is not None:
            metadata.update(user_metadata)
        
        target_address = _get_comfyui_address(props)
        log.info(f"准备发送数据到: {target_address}")
        log.debug(f"构建的元数据: {metadata}")
        success = comms.send_data(target_address, metadata, image_data)
        if success:
            msg = "Data sent to ComfyUI successfully."
            self.report({'OPERATOR'}, f"[INFO] {msg}")
            log.info("数据已成功发送到 ComfyUI。")
        else:
            msg = "Failed to send data! Please check the console log."
            self.report({'OPERATOR'}, f"[ERROR] {msg}")
            log.error("数据发送失败！请检查控制台日志。")
        
        if tempfile.gettempdir() in os.path.abspath(file_path):
            try:
                os.remove(file_path)
                log.info(f"已删除临时文件: {file_path}")
            except OSError as e:
                log.warning(f"删除临时文件失败: {file_path}. 原因: {e}")

        return {'FINISHED'}
