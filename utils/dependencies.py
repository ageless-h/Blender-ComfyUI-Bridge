import bpy
import sys
import subprocess
import os
import importlib

# 依赖项列表 (现在从 requirements.txt 读取)
_requirements_path = os.path.join(os.path.dirname(__file__), "..", "requirements.txt")

_dependencies_installed = False

def get_python_executable():
    """获取当前Blender实例使用的Python解释器路径。"""
    try:
        # Blender 2.9+
        return bpy.app.binary_path_python
    except AttributeError:
        # 兼容旧版本Blender
        return sys.executable

def install_pip():
    """确保pip已安装。"""
    try:
        import pip
    except ImportError:
        print("[Dependency] pip 未找到，正在尝试安装...")
        python_executable = get_python_executable()
        try:
            subprocess.run([python_executable, "-m", "ensurepip", "--user"], check=True, capture_output=True)
            print("[Dependency] pip 安装成功。")
        except subprocess.CalledProcessError as e:
            print(f"[Dependency] pip 安装失败: {e.stderr.decode()}")
            raise

def install_packages():
    """
    使用pip从 requirements.txt 安装所有列出的包。
    """
    python_executable = get_python_executable()
    
    print(f"[Dependency] 正在使用解释器: {python_executable}")
    print(f"[Dependency] 正在从文件安装依赖: {_requirements_path}")

    # --no-cache-dir: 防止缓存旧的或损坏的包
    # --use-pep517: 确保使用现代的构建后端
    # --upgrade: 如果已安装，则升级到指定版本
    command = [
        python_executable,
        "-m", "pip", "install",
        "--upgrade",
        "--no-cache-dir",
        "--use-pep517",
        "-r", _requirements_path
    ]

    try:
        # 使用 subprocess.run 来执行命令
        process = subprocess.run(command, check=True, capture_output=True, text=True)
        print("[Dependency] 依赖安装成功:")
        print(process.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("[Dependency] 依赖安装失败。")
        print("错误信息:")
        print(e.stderr)
        return False

def check_dependencies():
    """
    检查所有依赖是否已经安装。
    """
    global _dependencies_installed
    if _dependencies_installed:
        return True

    try:
        # 我们只检查一个核心依赖 'sshtunnel'。
        # 如果它能被导入，我们假设所有其他依赖也都已正确安装。
        importlib.import_module("sshtunnel")
        importlib.import_module("paramiko")
        importlib.import_module("zmq")
        importlib.import_module("msgspec")
        
        print("[Dependency] 所有依赖已满足。")
        _dependencies_installed = True
        return True
    except ImportError:
        print("[Dependency] 依赖缺失，需要安装。")
        return False

def ensure_dependencies():
    """
    确保所有依赖都已安装。如果未安装，则触发安装过程。
    """
    if check_dependencies():
        return

    print("=" * 40)
    print("      正在准备Blender-ComfyUI-Bridge插件")
    print("      首次启用时，需要下载并安装一些Python库。")
    print("      这个过程可能需要几分钟，请保持网络连接。")
    print("=" * 40)
    
    try:
        install_pip()
        if install_packages():
            print("[Dependency] 所有依赖已成功安装。请重启Blender以确保所有模块正确加载。")
            # 强制重载模块，以便在某些情况下可以立即使用
            importlib.invalidate_caches()
            global _dependencies_installed
            _dependencies_installed = True
        else:
            # 提示用户在Blender的偏好设置中查看插件的终端输出
            print("[Dependency] 安装失败。请打开Blender的系统控制台 (窗口 > 切换系统控制台) 查看详细错误日志。")

    except Exception as e:
        print(f"[Dependency] 发生未知错误: {e}") 