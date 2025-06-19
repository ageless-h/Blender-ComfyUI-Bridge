import bpy
import logging
from . import state

log = logging.getLogger(__name__)

def process_task_queue():
    """
    检查任务队列并处理一个项目。
    此函数设计为由 bpy.app.timers 运行。
    """
    if not state.task_queue.empty():
        try:
            # 从队列中获取任务
            image_path, image_name = state.task_queue.get_nowait()
            log.info(f"从队列中获取任务: 更新图像 '{image_name}' 使用路径 '{image_path}'")
            
            # 在主线程安全地更新 Blender 数据
            image = bpy.data.images.get(image_name)
            if not image:
                log.warning(f"目标图像 '{image_name}' 在Blender中未找到。将跳过更新。")
                return 0.5 # 检查间隔
            
            # 更新图像路径并重新加载
            image.filepath = image_path
            image.reload()
            
            log.info(f"图像 '{image_name}' 已成功更新。")

        except Exception as e:
            log.error(f"处理任务队列时出错: {e}", exc_info=True)
    
    return 0.5 # 返回再次运行的间隔时间（秒） 

def unregister_task_queue():
    """清理任务队列，以防插件卸载时有残留任务。"""
    while not state.task_queue.empty():
        try:
            state.task_queue.get_nowait()
        except state.task_queue.Empty:
            break
    log.info("任务队列已清空。") 