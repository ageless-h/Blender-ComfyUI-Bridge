import queue
import logging

log = logging.getLogger(__name__)

# 用于从 HTTP 接收线程向 Blender 主线程传递任务的队列
task_queue = queue.Queue()

# 用于持有后台线程的引用，以便在插件卸载时能安全地停止它
receiver_thread = None

def start_receiver_server(port):
    """启动或重启后台接收服务器"""
    from . import receiver # <-- 在函数内部进行局部导入
    
    global receiver_thread
    # 如果已有服务器在运行，先停止它
    if receiver_thread and receiver_thread.is_alive():
        log.info("检测到现有接收服务器，正在停止...")
        stop_receiver_server()

    log.info(f"正在端口 {port} 上启动新的接收服务器...")
    receiver_thread = receiver.HttpReceiver(port=port)
    receiver_thread.start()
    log.info("接收服务器已成功启动。")

def stop_receiver_server():
    """停止后台接收服务器"""
    global receiver_thread
    if receiver_thread and receiver_thread.is_alive():
        log.info("正在停止接收服务器...")
        try:
            receiver_thread.stop()
            receiver_thread.join(timeout=5)
            if receiver_thread.is_alive():
                log.warning("接收线程在超时后仍未停止。")
        except Exception as e:
            log.error(f"停止接收线程时发生错误: {e}", exc_info=True)
        finally:
            receiver_thread = None
            log.info("接收服务器已停止。")
    elif receiver_thread:
        log.warning("接收线程对象存在但未存活。重置引用。")
        receiver_thread = None
    else:
        log.info("接收服务器未在运行。")
