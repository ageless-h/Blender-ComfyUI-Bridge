import queue

# 用于从 HTTP 接收线程向 Blender 主线程传递任务的队列
task_queue = queue.Queue()

# 用于持有后台线程的引用，以便在插件卸载时能安全地停止它
receiver_thread = None
