import threading
import time
import logging

log = logging.getLogger(__name__)

# --- 全局状态变量 ---
# 使用一个字典来存储全局的隧道管理器实例，确保单例模式
_tunnel_manager_instance = None
_tunnel_lock = threading.Lock()

class SSHTunnelManager:
    """
    管理SSH隧道的单例类。
    通过创建两个独立的Forwarder实例来负责启动、停止和维护双向隧道。
    """
    def __init__(self, ssh_settings):
        """
        初始化隧道管理器。
        
        :param ssh_settings: 包含SSH连接参数的Blender属性组。
        """
        self.local_forwarder = None   # For Blender -> ComfyUI
        self.remote_forwarder = None  # For ComfyUI -> Blender
        self.thread_local = None
        self.thread_remote = None
        
        self.is_running = False
        self.error = None
        
        # --- 从Blender属性中提取连接参数 ---
        self.ssh_host = ssh_settings.ssh_host
        # 端口现在是字符串，需要转换为整数
        try:
            self.ssh_port = int(ssh_settings.ssh_port)
        except (ValueError, TypeError):
            self.error = f"内部错误：SSH端口 '{ssh_settings.ssh_port}' 不是一个有效的数字。"
            log.error(f"[SSH] Error: {self.error}")
            return

        self.ssh_user = ssh_settings.ssh_user
        self.ssh_password = ssh_settings.ssh_password if ssh_settings.ssh_password else None
        self.ssh_key = ssh_settings.ssh_key_path if ssh_settings.ssh_key_path else None
        
        # --- 解析远程和本地端口 ---
        try:
            remote_host, remote_port_str = ssh_settings.comfyui_address.split(':')
            self.remote_comfyui_port = int(remote_port_str)
            self.local_zmq_port = self.remote_comfyui_port
            self.local_http_port = ssh_settings.blender_receiver_port
        except ValueError as e:
            self.error = f"无法解析地址和端口: {e}"
            log.error(f"[SSH] Error: {self.error}")
            return

        # Lazy import sshtunnel
        from sshtunnel import SSHTunnelForwarder

        # --- 配置本地转发器 (Blender -> ComfyUI) ---
        self.local_forwarder = SSHTunnelForwarder(
            (self.ssh_host, self.ssh_port),
            ssh_username=self.ssh_user,
            ssh_password=self.ssh_password,
            ssh_pkey=self.ssh_key,
            remote_bind_address=(remote_host, self.remote_comfyui_port),
            local_bind_address=('127.0.0.1', self.local_zmq_port),
            set_keepalive=10,
        )

        # --- 配置远程转发器 (ComfyUI -> Blender) ---
        self.remote_forwarder = SSHTunnelForwarder(
            (self.ssh_host, self.ssh_port),
            ssh_username=self.ssh_user,
            ssh_password=self.ssh_password,
            ssh_pkey=self.ssh_key,
            remote_bind_addresses=[('127.0.0.1', self.local_http_port)],
            local_bind_addresses=[('127.0.0.1', self.local_http_port)],
            set_keepalive=10,
        )

    def _run_forwarder(self, forwarder, name):
        """
        Starts a forwarder and keeps the thread alive in a loop until
        the manager's `is_running` flag is set to False.
        """
        from sshtunnel import BaseSSHTunnelForwarderError
        try:
            log.info(f"[SSH] {name} 转发器线程启动...")
            forwarder.start()
            # This loop is the new crucial part. It keeps the thread alive.
            while self.is_running:
                time.sleep(0.5)
        except BaseSSHTunnelForwarderError as e:
            self.error = f"SSH 隧道错误 ({name}): {e}"
            log.error(f"[SSH] Error in {name} forwarder: {self.error}")
            self.is_running = False # Signal other threads to stop
        except Exception as e:
            self.error = f"未知错误在 {name} 转发器: {e}"
            log.error(f"[SSH] Error: {self.error}")
            self.is_running = False
        finally:
            if forwarder.is_active:
                forwarder.stop()
            log.info(f"[SSH] {name} 转发器线程已停止。")

    def start(self):
        """启动两个隧道转发器，每个都在自己的线程中。"""
        if self.is_running or self.error:
            return
            
        log.info("[SSH] 正在启动双向隧道...")
        self.is_running = True # Set state to running before starting threads

        self.thread_local = threading.Thread(target=self._run_forwarder, args=(self.local_forwarder, "Local->Remote"), daemon=True)
        self.thread_remote = threading.Thread(target=self._run_forwarder, args=(self.remote_forwarder, "Remote->Local"), daemon=True)
        
        self.thread_local.start()
        self.thread_remote.start()

    def stop(self):
        """停止所有活动的隧道。"""
        if not self.is_running:
            return
        
        log.info("[SSH] 正在停止双向隧道...")
        
        self.is_running = False # This will signal the _run_forwarder loops to exit.
        
        if self.thread_local and self.thread_local.is_alive():
            self.thread_local.join(timeout=2)
        if self.thread_remote and self.thread_remote.is_alive():
            self.thread_remote.join(timeout=2)
        
        log.info("[SSH] 隧道已停止。")

def get_tunnel_manager(ssh_settings=None):
    """
    获取SSHTunnelManager的单例实例。
    如果实例不存在，则使用提供的设置创建一个新实例。
    """
    global _tunnel_manager_instance
        with _tunnel_lock:
            if _tunnel_manager_instance is None and ssh_settings:
                log.info("[SSH] 创建新的隧道管理器实例。")
                _tunnel_manager_instance = SSHTunnelManager(ssh_settings)
        return _tunnel_manager_instance

def stop_tunnel():
    """全局函数，用于停止活动的隧道实例。"""
    global _tunnel_manager_instance
    with _tunnel_lock:
        if _tunnel_manager_instance:
            log.info("[SSH] 正在通过全局函数停止隧道。")
            _tunnel_manager_instance.stop()
            _tunnel_manager_instance = None

def get_tunnel_status():
    """获取当前隧道的状态。"""
    if _tunnel_manager_instance is None:
        return "INACTIVE", None
    
    if _tunnel_manager_instance.error:
        return "ERROR", _tunnel_manager_instance.error
    
    if not _tunnel_manager_instance.is_running:
        return "INACTIVE", None

    local_ok = _tunnel_manager_instance.local_forwarder and _tunnel_manager_instance.local_forwarder.is_active
    remote_ok = _tunnel_manager_instance.remote_forwarder and _tunnel_manager_instance.remote_forwarder.is_active
    
    if local_ok and remote_ok:
        return "ACTIVE", None
    
    # If threads have died without setting an error, report it
    local_thread_alive = _tunnel_manager_instance.thread_local and _tunnel_manager_instance.thread_local.is_alive()
    remote_thread_alive = _tunnel_manager_instance.thread_remote and _tunnel_manager_instance.thread_remote.is_alive()
    if not local_thread_alive or not remote_thread_alive:
        _tunnel_manager_instance.error = "一个隧道线程意外终止。"
        return "ERROR", _tunnel_manager_instance.error

    return "INACTIVE", None # Tunnels are starting but not active yet 