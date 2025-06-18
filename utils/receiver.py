import threading
import logging
import json
import tempfile
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from .state import task_queue

log = logging.getLogger(__name__)

class ReceiverRequestHandler(BaseHTTPRequestHandler):
    """处理来自 ComfyUI 的 HTTP POST 请求。"""
    
    # 将 server 实例的引用传递给 handler
    def __init__(self, request, client_address, server):
        self.image_name_override = server.image_name_override
        super().__init__(request, client_address, server)

    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            content_type = self.headers['Content-Type']
            
            # 从请求头中获取目标图像名称
            image_name = self.headers.get('X-Blender-Image-Name', self.image_name_override)
            if not image_name:
                log.error("未在请求头或服务器配置中找到目标图像名称。")
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Bad Request: Missing X-Blender-Image-Name header')
                return

            log.info(f"收到 POST 请求，目标图像: {image_name}, 类型: {content_type}")

            if 'application/json' in content_type:
                # 本地模式：ComfyUI 发送包含图像路径的 JSON
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data)
                image_path = data.get('image_path')
                log.info(f"本地模式：收到图像路径 '{image_path}'")
                task_queue.put((image_path, image_name))
            else:
                # 远程模式：ComfyUI 直接发送图像二进制数据 (e.g., image/png)
                image_data = self.rfile.read(content_length)
                
                # 将二进制数据保存到临时文件
                # 使用带后缀的命名临时文件以帮助Blender识别文件类型
                suffix = f".{content_type.split('/')[-1]}" if '/' in content_type else ".tmp"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="blender_bridge_") as tmp_file:
                    tmp_file.write(image_data)
                    temp_path = tmp_file.name
                
                log.info(f"远程模式：图像已保存到临时文件 '{temp_path}'")
                task_queue.put((temp_path, image_name))

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
            
        except Exception as e:
            log.error(f"处理 POST 请求时出错: {e}", exc_info=True)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'Internal Server Error')
    
    def log_message(self, format, *args):
        # 将http.server的默认日志重定向到我们的日志记录器
        log.debug(format % args)


class BlenderReceiverServer(HTTPServer):
    """自定义的 HTTPServer，用于传递额外参数给 RequestHandler。"""
    def __init__(self, server_address, RequestHandlerClass, image_name_override=None):
        self.image_name_override = image_name_override
        super().__init__(server_address, RequestHandlerClass)


class HttpReceiver(threading.Thread):
    """在一个独立的线程中运行 HTTP 服务器。"""
    def __init__(self, port, image_name_override=None):
        super().__init__(daemon=True)
        self.port = port
        self.image_name_override = image_name_override
        self.server = None

    def run(self):
        try:
            # 传递 image_name_override 到 handler
            def handler_factory(*args, **kwargs):
                return ReceiverRequestHandler(*args, **kwargs)

            self.server = BlenderReceiverServer(("", self.port), handler_factory, self.image_name_override)
            
            log.info(f"正在端口 {self.port} 上启动 Blender HTTP 接收服务器...")
            self.server.serve_forever()
            log.info("Blender HTTP 接收服务器已停止。")

        except Exception as e:
            log.error(f"无法启动或运行 HTTP 服务器: {e}", exc_info=True)

    def stop(self):
        if self.server:
            log.info("正在关闭 Blender HTTP 接收服务器...")
            self.server.shutdown() # 安全地停止 serve_forever() 循环
            self.server.server_close() # 释放端口
            self.server = None
