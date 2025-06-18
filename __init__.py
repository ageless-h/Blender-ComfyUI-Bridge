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
classes = (
    properties.BridgeProperties,
    panel.BRIDGE_PT_MainPanel,
    panel.BRIDGE_PT_ConnectionSettingsPanel,
    operators.BRIDGE_OT_TestConnection,
    operators.BRIDGE_OT_RenderAndSend,
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
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.bridge_props = bpy.props.PointerProperty(type=properties.BridgeProperties)

    state.receiver_thread = threading.Thread(target=receiver.run_server, daemon=True)
    state.receiver_thread.start()
    log.info(f"Receiver thread started on port {state.get_blender_port()}.")

    # 使用 bpy.app.timers 注册我们的后台任务，这是一个更稳健的方法
    if not bpy.app.timers.is_registered(tasks.process_task_queue):
        bpy.app.timers.register(tasks.process_task_queue, first_interval=1.0)
        log.info("Task queue processor registered.")

    log.info("Addon registration complete.")


def unregister():
    """插件卸载函数"""
    log.info("Unregistering Blender-ComfyUI-Bridge addon...")
    
    # 注销后台任务定时器
    if bpy.app.timers.is_registered(tasks.process_task_queue):
        bpy.app.timers.unregister(tasks.process_task_queue)
        log.info("Task queue processor unregistered.")

    # 停止后台服务
    if state.receiver_thread and state.receiver_thread.is_alive():
        log.info("Stopping receiver thread...")
        state.receiver_thread.stop()
        state.receiver_thread.join(timeout=5)
    
    if hasattr(bpy.types.Scene, 'bridge_props'):
        del bpy.types.Scene.bridge_props

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    # 停止任务队列
    tasks.unregister_task_queue()

    log.info("Addon unregistration complete.")
