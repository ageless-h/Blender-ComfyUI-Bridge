import zmq
import msgspec
import logging

# 获取一个日志记录器
log = logging.getLogger(__name__)

# 创建一个可重用的全局ZMQ上下文
# ZMQ上下文是线程安全的
context = zmq.Context()

def send_request(address, data, timeout=5000):
    """一个通用函数，用于向ZMQ地址发送请求并等待回复。"""
    encoder = msgspec.msgpack.Encoder()
    decoder = msgspec.msgpack.Decoder()
    
    packed_request = encoder.encode(data)
    
    socket = None  # 确保 socket 变量在 try 块外可用
    try:
        # 1. 创建 ZMQ REQ socket
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, timeout)
        socket.setsockopt(zmq.SNDTIMEO, timeout)

        # 2. 连接并发送
        log.info(f"Connecting to ZMQ server: {address}...")
        socket.connect(address)
        socket.send(packed_request)

        # 3. 等待回复
        packed_reply = socket.recv()
        
        # 4. 解码并返回
        return decoder.decode(packed_reply)

    except msgspec.DecodeError as e:
        log.error(f"Failed to decode MessagePack response: {e}")
        return None
    except zmq.error.Again as e:
        # 此异常在超时 (EAGAIN) 时引发
        log.warning(f"ZMQ request to {address} timed out.")
        return None
    except Exception as e:
        log.error(f"An unexpected ZMQ error occurred: {e}", exc_info=True)
        return None
    finally:
        # 6. 确保 socket 被关闭
        if socket:
            log.info("Closing ZMQ socket.")
            socket.close()

def send_ping(address, timeout=2000):
    """向服务器发送一个简单的 ping，只检查是否收到回复，不关心内容。"""
    log.info(f"Pinging {address}...")
    socket = None
    try:
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, timeout)
        socket.setsockopt(zmq.SNDTIMEO, timeout)
        socket.connect(address)
        
        encoder = msgspec.msgpack.Encoder()
        socket.send(encoder.encode({"type": "ping"}))
        
        socket.recv()
        log.info("Ping successful.")
        return True

    except zmq.error.Again:
        log.warning(f"Ping timed out to {address}.")
        return False
    except Exception as e:
        log.error(f"An unexpected error occurred during ping: {e}", exc_info=True)
        return False
    finally:
        if socket:
            socket.close()

def send_data(address, data):
    """向服务器发送实际的数据。"""
    log.info(f"Sending data to {address}: {data}")
    try:
        response = send_request(address, data)
        if response and response.get("status") == "ok":
            return True
        else:
            log.warning(f"Received unexpected reply after sending data: {response}")
            return False
    except Exception as e:
        log.error(f"An unknown exception occurred during sending data: {e}", exc_info=True)
        return False
