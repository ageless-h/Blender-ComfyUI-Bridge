# ComfyUI-BlenderBridge - Blender 插件技术对接文档

**版本:** 2.0
**日期:** 2025年6月18日
**状态:** Blender 插件已定稿，待 ComfyUI 端对接

---

## 1. 概述

本文档旨在为 ComfyUI 端的工程师提供与 `ComfyUI-BlenderBridge` Blender 插件进行技术对接所需的所有信息。Blender 插件负责将渲染任务和元数据发送到 ComfyUI，并接收处理后的图像结果。

通信建立在 **ZMQ (REQ/REP 模式)** 和 **HTTP** 两个协议之上。

-   **ZMQ (Blender -> ComfyUI):** 用于从 Blender 发送指令和数据到 ComfyUI 的自定义 ZMQ 节点。
-   **HTTP (ComfyUI -> Blender):** 用于从 ComfyUI 的工作流中将生成的图像异步地回传给 Blender。

---

## 2. ZMQ 通信协议 (Blender -> ComfyUI)

Blender 插件通过一个 ZMQ REQ (请求) 套接字，向 ComfyUI 端的 ZMQ REP (回复) 服务器发送请求。

-   **地址:** 可在 Blender 插件的UI中配置，默认为 `tcp://127.0.0.1:5555`。
-   **数据格式:** 所有交换的数据都必须使用 **MessagePack** 进行序列化。

### 2.1 请求类型

#### a) Ping (连接测试)

此请求用于测试两端之间的基本连接是否畅通。

-   **Blender 发送的请求体 (MessagePack 格式):**
    ```json
    {
        "type": "ping"
    }
    ```

-   **ComfyUI 节点应有的行为:**
    1.  收到消息后，解码并检查 `type` 字段是否为 `"ping"`。
    2.  **关键:** 如果是 `ping` 请求，**必须立即停止处理，不得将此消息传递给下游的任何节点或工作流。**
    3.  **立即回复一个简单的成功信号**。Blender 插件端当前实现为**只要收到任何回复**即视为成功，但为了未来的健壮性，建议 ComfyUI 端回复一个固定的成功消息。
    4.  **建议的 ComfyUI 回复 (MessagePack 格式):**
        ```json
        {
            "status": "ok",
            "message": "pong"
        }
        ```

#### b) Render & Send (数据提交)

此请求用于发送实际的渲染任务和元数据。

-   **Blender 发送的请求体 (MessagePack 格式):**
    ```json
    {
        "type": "render_and_return",
        "render_path": "C:\\path\\to\\temp\\render_result.png",
        "return_info": {
            "blender_server_address": "http://127.0.0.1:5556",
            "image_datablock_name": "MyRenderResult"
        }
    }
    ```
    -   `type`: 固定的字符串 `"render_and_return"`。
    -   `render_path`: Blender 渲染出的图像在磁盘上的**绝对路径**。ComfyUI 的工作流应从此路径加载图像。
    -   `return_info`: 一个包含回传信息的重要字典。
        -   `blender_server_address`: Blender 端内置 HTTP 接收服务器的完整地址 (包含 `http://` 和端口)。ComfyUI 工作流处理完图像后，**必须向此地址发送一个 HTTP POST 请求**来回传结果。
        -   `image_datablock_name`: 目标图像在 Blender 内部的名称。此名称必须在回传时通过 HTTP 头原样返回。

-   **ComfyUI 节点应有的行为:**
    1.  解码消息，检查 `type` 是否为 `"render_and_return"`。
    2.  解析 `render_path` 并将其作为文件路径传递给工作流的 "Load Image" 节点。
    3.  将 `return_info` 字典完整地传递到工作流的末端，最终交给负责回传图像的节点。
    4.  工作流执行成功后，回复一个确认消息。
    5.  **建议的 ComfyUI 回复 (MessagePack 格式):**
        ```json
        {
            "status": "ok",
            "message": "Workflow received and started."
        }
        ```

---

## 3. HTTP 通信协议 (ComfyUI -> Blender)

当 ComfyUI 的工作流完成图像处理后，需要通过一个 HTTP POST 请求将结果发送回 Blender。

-   **目标地址:** 从 ZMQ 请求中获取的 `blender_server_address`。
-   **HTTP 方法:** `POST`

### 3.1 HTTP 请求细节

#### a) 远程模式 (标准)

当 ComfyUI 和 Blender 在不同机器上，或需要通过网络传输时。

-   **HTTP Headers (必须包含):**
    -   `Content-Type`: 图像的 MIME 类型, 例如 `image/png` 或 `image/jpeg`。
    -   `X-Blender-Image-Name`: **必须**包含从 ZMQ 请求中收到的 `image_datablock_name` 的值。

-   **HTTP Body:**
    -   完整的、原始的图像二进制数据。

#### b) 本地模式 (优化)

当 ComfyUI 和 Blender 在同一台机器上运行时，为避免不必要的数据拷贝，可以采用路径传输模式。

-   **HTTP Headers (必须包含):**
    -   `Content-Type`: `application/json`
    -   `X-Blender-Image-Name`: **必须**包含从 ZMQ 请求中收到的 `image_datablock_name` 的值。

-   **HTTP Body (JSON 格式):**
    ```json
    {
        "image_path": "C:\\path\\to\\final_comfyui_output.png"
    }
    ```
    -   `image_path`: 最终生成的图像在磁盘上的绝对路径。Blender 将直接从此路径加载图像。

---

## 4. 总结

-   Blender 插件是**客户端 (REQ)**，ComfyUI 节点是**服务器端 (REP)**。
-   所有 ZMQ 通信都使用 **MessagePack** 编码。
-   **`ping` 请求必须被特殊处理**，不能触发工作流。
-   `render_and_return` 请求提供了图像加载和结果回传所需的所有信息。
-   图像回传通过 **HTTP POST** 完成，利用 `X-Blender-Image-Name` 头来识别目标。

如有任何疑问，请随时沟通。 