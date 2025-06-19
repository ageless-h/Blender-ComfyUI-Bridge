import threading
import logging
import json
import tempfile
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import bpy
from .state import task_queue

log = logging.getLogger(__name__)


class ReceiverRequestHandler(BaseHTTPRequestHandler):
    """处理来自 ComfyUI 的 HTTP POST 请求。"""

    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            content_type = self.headers['Content-Type']

            # 从 server 实例获取目标图像名称
            target_image_name = self.server.target_image_name
            if not target_image_name:
                log.error("接收服务器未配置目标图像名称。")
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Bad Request: Target image not configured on Blender side.')
                return

            log.info(f"收到 POST 请求，目标图像: '{target_image_name}'")

            # 所有情况都将接收到的数据保存为临时文件
            image_data = self.rfile.read(content_length)
            suffix = f".{content_type.split('/')[-1]}" if '/' in content_type else ".tmp"
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                tmp_file.write(image_data)
                temp_path = tmp_file.name
            
            log.info(f"数据已保存到临时文件: '{temp_path}'")
            task_queue.put((temp_path, target_image_name))

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')

        except Exception as e:
            log.error(f"处理 POST 请求时出错: {e}", exc_info=True)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'Internal Server Error')

    def log_message(self, format, *args):
        log.debug(format % args)


class BlenderReceiverServer(HTTPServer):
    """自定义的 HTTPServer，用于持有目标图像名称。"""
    def __init__(self, server_address, RequestHandlerClass, target_image_name):
        self.target_image_name = target_image_name
        super().__init__(server_address, RequestHandlerClass)


class HttpReceiver(threading.Thread):
    """在一个独立的线程中运行 HTTP 服务器。"""
    def __init__(self, port):
        super().__init__(daemon=True)
        self.port = port
        self.server = None

    def run(self):
        try:
            # 启动时从Blender主线程获取当前的目标图像名称
            context = bpy.context
            target_image_name = context.scene.bridge_props.target_image_datablock.name if context.scene.bridge_props.target_image_datablock else None

            if not target_image_name:
                log.error("无法启动接收服务器：未在Blender中设置目标图像。")
                return

            self.server = BlenderReceiverServer(("", self.port), ReceiverRequestHandler, target_image_name)
            
            log.info(f"正在端口 {self.port} 上启动 Blender HTTP 接收服务器...")
            self.server.serve_forever()
            log.info("Blender HTTP 接收服务器已停止。")

        except Exception as e:
            log.error(f"无法启动或运行 HTTP 服务器: {e}", exc_info=True)

    def stop(self):
        if self.server:
            log.info("正在关闭 Blender HTTP 接收服务器...")
            self.server.shutdown()
            self.server.server_close()
            self.server = None
