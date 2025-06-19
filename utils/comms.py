import zmq
import msgspec
import logging

# 获取一个日志记录器
log = logging.getLogger(__name__)

# 创建一个可重用的全局ZMQ上下文
# ZMQ上下文是线程安全的
context = zmq.Context()

def _prepare_address(address):
    """确保地址包含 tcp:// 协议头"""
    if not address.startswith('tcp://'):
        return f'tcp://{address}'
    return address

def send_request(address, data, timeout=5000):
    """一个通用函数，用于向ZMQ地址发送请求并等待回复。"""
    address = _prepare_address(address)
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
    address = _prepare_address(address)
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

def send_data(address, metadata, image_data=None, timeout=10000):
    """
    向服务器发送元数据，并可选择性地附加图像二进制数据。
    
    :param address: 服务器地址
    :param metadata: 要发送的元数据 (字典)
    :param image_data: (可选) 图像的原始二进制数据
    :param timeout: 超时时间 (毫秒)
    :return: 成功时返回 True，否则返回 False
    """
    address = _prepare_address(address)
    log.info(f"Sending data to {address}: {metadata}")
    
    encoder = msgspec.msgpack.Encoder()
    decoder = msgspec.msgpack.Decoder()
    
    packed_metadata = encoder.encode(metadata)
    
    socket = None
    try:
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, timeout)
        socket.setsockopt(zmq.SNDTIMEO, timeout)
        socket.connect(address)
        
        # 构建消息
        message_parts = [packed_metadata]
        if image_data:
            log.info(f"Attaching image data ({len(image_data)} bytes).")
            message_parts.append(image_data)
        
        # 发送多部分消息
        socket.send_multipart(message_parts)

        # 等待回复
        packed_reply = socket.recv()
        response = decoder.decode(packed_reply)

        if response and response.get("status") == "ok":
            return True
        else:
            log.warning(f"Received unexpected reply: {response}")
            return False

    except msgspec.DecodeError as e:
        log.error(f"Failed to decode MessagePack response: {e}")
        return False
    except zmq.error.Again:
        log.warning(f"ZMQ request to {address} timed out.")
        return False
    except Exception as e:
        log.error(f"An unexpected ZMQ error occurred: {e}", exc_info=True)
        return False
    finally:
        if socket:
            log.info("Closing ZMQ socket.")
            socket.close()
