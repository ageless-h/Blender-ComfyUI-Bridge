# Diagnostic build to test the wheel installation mechanism.
import bpy
import logging
import threading

from . import properties
from . import panel
from . import operators
from .utils import state, receiver, tasks

# --- 日志配置 ---
log = logging.getLogger("bl_ext.user_default.blender_comfyui_bridge")
if not log.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.INFO)

# --- 插件类 ---
# panel 模块现在有自己的注册函数，所以我们从这里移除它们
classes = (
    properties.BridgeProperties,
    operators.BRIDGE_OT_TestConnection,
    operators.BRIDGE_OT_SendData, # 替换为新的 Operator
)

bl_info = {
    "name": "Blender-ComfyUI-Bridge",
    "author": "Your Name",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > ComfyUI",
    "description": "Bridges Blender and ComfyUI for rendering workflows",
    "warning": "",
    "doc_url": "",
    "category": "Render",
    "id": "blender_comfyui_bridge",
}

def register():
    """插件注册函数"""
    log.info("Registering Blender-ComfyUI-Bridge addon...")
    
    panel.register()

    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.bridge_props = bpy.props.PointerProperty(type=properties.BridgeProperties)

    # 启动后台接收服务器
    # 我们无法在注册时访问 context.scene.bridge_props。
    # 在类被注册后，我们可以通过 RNA 系统安全地获取属性的默认值。
    default_port = properties.BridgeProperties.bl_rna.properties['blender_receiver_port'].default
    state.start_receiver_server(default_port)

    # 使用 bpy.app.timers 注册我们的后台任务
    if not bpy.app.timers.is_registered(tasks.process_task_queue):
        bpy.app.timers.register(tasks.process_task_queue, first_interval=1.0)
        log.info("Task queue processor registered.")

    log.info("Addon registration complete.")


def unregister():
    """插件卸载函数"""
    log.info("Unregistering Blender-ComfyUI-Bridge addon...")
    
    panel.unregister()

    # 注销后台任务定时器
    if bpy.app.timers.is_registered(tasks.process_task_queue):
        bpy.app.timers.unregister(tasks.process_task_queue)
        log.info("Task queue processor unregistered.")

    # 停止后台服务
    state.stop_receiver_server()
    
    if hasattr(bpy.types.Scene, 'bridge_props'):
        del bpy.types.Scene.bridge_props

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    # 停止任务队列
    tasks.unregister_task_queue()

    log.info("Addon unregistration complete.")
