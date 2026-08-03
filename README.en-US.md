

# Blender-ComfyUI Bridge

[![GitHub Repo stars](https://img.shields.io/github/stars/ageless-h/Blender-ComfyUI-Bridge?style=social)](https://github.com/ageless-h/Blender-ComfyUI-Bridge/stargazers)

A Blender plugin that serves as a bridge for real-time, two-way communication between Blender and ComfyUI.

This plugin allows you to seamlessly send render results or image data with a single click from Blender to a preset ComfyUI workflow for processing, and then automatically return the processed image back to Blender.

## ✨ Features

*   **One-Click Data Sending**: Provides a clean UI panel in the 3D Viewport sidebar. Click the button to render the current scene and send image data to ComfyUI.
*   **Robust Image Format Support**:
    *   **Standard Images (PNG/JPG)**: Quickly send preview images.
    *   **Multi-Channel EXR (Multi-Layer EXR)**: Losslessly packages all render passes (e.g., `Depth`, `Mist`, `Normal`, `AO`, etc.) into a single EXR file for sending, providing maximum flexibility for downstream image processing.
*   **Flexible Network Connectivity**:
    *   **Direct Connection**: Connect directly to ComfyUI in a local network environment.
    *   **SSH Tunneling**: Built-in SSH tunnel feature allows you to seamlessly connect a local Blender instance to ComfyUI on a remote server via a secure SSH connection, without manually configuring port forwarding.
*   **Intelligent Data Transfer**: The plugin sends image binary data directly through memory, eliminating the need for a shared file system, and supports complex network environments across machines and containers.
*   **Real-Time Connection Status**: The UI displays the connection status with ComfyUI in real-time (Connected/Disconnected).
*   **Two-Way Communication**:
    *   **Blender -> ComfyUI**: Sends render tasks, metadata, and image binary data via ZMQ.
    *   **ComfyUI -> Blender**: Sends processed image data back to Blender via HTTP.
*   **Fully Automated Dependency Management**: Upon first activation, the plugin automatically installs all required dependency libraries (`sshtunnel`, `paramiko`, `pyzmq`, `msgspec`) using Blender's built-in Python environment, with no manual intervention required.
*   **Background Task Processing**: Uses Blender's `bpy.app.timers` to stably handle asynchronous tasks from ComfyUI without blocking the UI.
*   **Robust Error Handling**: Includes connection testing, timeout, and error reporting mechanisms.

## 🚀 Installation Guide

### Prerequisites

- **Blender**: Version 4.0 or higher
- **ComfyUI**: A running server instance
- **Network**: Stable internet connection (for dependency installation)

### 1. ComfyUI Node

First, ensure you have installed a compatible receiver node in ComfyUI. This node must be capable of handling multipart ZMQ messages from Blender.

**Recommended Node**: Search for "Blender Bridge" in [ComfyUI-Manager](https://github.com/Comfy-Org/ComfyUI-Manager) or directly install the accompanying receiver node for this plugin.

### 2. Blender Plugin Installation

#### Method 1: Install from GitHub Releases (Recommended)

**Steps**:

1. **Download the Plugin**
   - Visit the [Releases page](https://github.com/ageless-h/Blender-ComfyUI-Bridge/releases)
   - Download the latest `Blender-ComfyUI-Bridge-vX.X.zip` file
   - Example: `Blender-ComfyUI-Bridge-v1.0.0.zip`

2. **Install in Blender**
   ```
   Blender -> Edit -> Preferences -> Add-ons
   ```

3. **Install File**
   - Click the `Install...` button
   - Select the `.zip` file you just downloaded
   - Wait for installation to complete

4. **Enable Plugin**
   - Find "Blender-ComfyUI Bridge" in the add-on list
   - Check the box to enable the add-on
   - Click `Save User Settings`

5. **Automatic Dependency Installation**
   - The plugin will automatically detect and install required dependencies upon first activation
   - Open `Window -> Toggle System Console` to view installation logs
   - Wait for installation to complete (may take from tens of seconds to a few minutes)
   - **Important**: It is recommended to restart Blender after installation is complete

#### Method 2: Manual Installation (Advanced Users)

1. **Clone Repository**
   ```bash
   git clone https://github.com/ageless-h/Blender-ComfyUI-Bridge.git
   cd Blender-ComfyUI-Bridge
   ```

2. **Copy Plugin Directory**
   - Copy the `blender_addon` directory to Blender's add-ons directory:
     ```
     # Windows
     C:\Users\YourName\AppData\Roaming\Blender Foundation\Blender\4.0\scripts\addons\

     # macOS
     /Users/YourName/Library/Application Support/Blender/4.0/scripts/addons/

     # Linux
     ~/.config/blender/4.0/scripts/addons/
     ```

3. **Manually Install Dependencies** (if automatic installation fails)
   ```bash
   cd blender_addon
   pip install -r requirements.txt
   ```

### 3. Verify Installation

1. Open Blender
2. Press `N` to open the sidebar
3. Check if you see the `ComfyUI` tab
4. If you see it, installation is successful! ✅

## 🔧 Usage

### Basic Workflow

#### Step 1: Open Blender and Locate the Plugin Panel

1. In Blender's 3D Viewport, press `N` to open the sidebar
2. Scroll down to find the `ComfyUI` tab

![面板位置示例](https://capsule-render.vercel.app/api?type=header&text=Blender+ComfyUI+Bridge&fontSize=24)

#### Step 2: Configure Connection

##### Direct Connection Mode

**Applicable Scenario**: ComfyUI and Blender are on the same machine or local network

1. In the "Connection Settings" area, uncheck "Enable SSH Tunnel"
2. Enter the ZMQ address of the ComfyUI server
   - Local default: `127.0.0.1:5555`
   - Verify ComfyUI's ZMQ port (usually 5555)
3. Click the "Test Connection" button
4. Wait for the status to change to "Connected" (green)

##### SSH Tunnel Mode

**Applicable Scenario**: ComfyUI is on a remote server

1. Check "Enable SSH Tunnel"
2. Fill in SSH server information:
   - **Host**: `192.168.1.100` (example IP)
   - **Port**: `22` (default SSH port)
   - **Username**: `your-username`
   - **Password**: Or select **Private Key** path
3. **Important**: The address filled in "ComfyUI Server Address" is **relative to the SSH server**
   - For example: If ComfyUI runs on the SSH server, typically enter `127.0.0.1:5555`
   - If ComfyUI is on another machine, enter the actual IP address, e.g., `192.168.1.200:5555`
4. Click the "Establish SSH Tunnel" button
5. Wait for the tunnel to be successfully established (status shows "Connected")

#### Step 3: Select Result Receiver

1. In the "Result Receiver" area, click the folder icon
2. Select a Blender Image Data Block
3. It is best to choose an empty data block for easier result reception

#### Step 4: Send Data

**Send Render Results**:

1. Select the "Render Result" tab
2. Select image format:
   - **Standard Image (PNG/JPG)**: Suitable for quick preview
   - **Multi-Channel EXR**: Includes all render passes (Depth, Normal, AO, etc.)
3. Click the "Render and Send" button
4. Blender will render the current scene and send the image data to ComfyUI

**Send Existing Image**:

1. Switch to the "Image Editor" tab
2. Open the image you want to send
3. Click the "Send Current Image" button
4. The image will be sent to ComfyUI

#### Step 5: Receive Results

1. Once ComfyUI finishes processing, the result will automatically appear in the image data block you selected in Step 3
2. You can view the processed result in Blender's Image Editor

## 💡 Usage Examples

### Example 1: Local Render Workflow

**Scenario**: Render a character in Blender, then apply stylization in ComfyUI.

```
Blender (Local)
├─ Render Character
├─ Send render result to ComfyUI
├─ ComfyUI (Local Network)
│  ├─ Stylize processing
│  ├─ Generate stylized image
│  └─ Return result to Blender
└─ Blender receives and displays result
```

**Effect**: Rapid iteration local + AI workflow, no manual file transfer required.

### Example 2: Remote Render Workflow (SSH Tunnel)

**Scenario**: Model in local Blender, render on remote ComfyUI server, connected via SSH tunnel.

```
Blender (Local)
├─ Send model data to ComfyUI
├─ Connect via SSH tunnel
├─ ComfyUI (Remote Server)
│  ├─ High-quality rendering
│  ├─ Generate render result
│  └─ Return to Blender via HTTP
└─ Blender receives and displays
```

**Advantages**:
- Leverage the powerful GPU of the remote server
- Save local computing resources
- Support cross-platform workflow

### Example 3: Batch Image Processing

**Scenario**: Send multiple different scenes rendered in Blender to ComfyUI for batch processing.

```
1. Scene 1 render → Send to ComfyUI
2. Scene 2 render → Send to ComfyUI
3. Scene 3 render → Send to ComfyUI
4. ComfyUI batch processes and returns all results
```

**Workflow Tips**:
- You can set up different output data blocks in Blender to conveniently receive results for different scenes

## 📋 FAQ

### Q1: What if I don't see the sidebar after enabling the plugin?

**A**: Follow these troubleshooting steps:
1. Ensure the add-on is enabled (Edit -> Preferences -> Add-ons -> Check)
2. Restart Blender (close completely and reopen)
3. Press `N` to open the sidebar
4. If still not visible, check the Blender console for error messages

### Q2: Connection test failed, shows "Disconnected"

**A**: Check the following items:
1. **Is ComfyUI running?** Ensure the ComfyUI server is active
2. **Is the ZMQ port correct?** Default is `5555`, verify ComfyUI's ZMQ port
3. **Firewall?** Check if local or remote server firewalls are blocking the connection
4. **Is the address correct?**
   - Direct connection: `127.0.0.1:5555`
   - SSH tunnel: Ensure it's the address relative to the SSH server
5. Try using ComfyUI's IP address instead of `localhost`

### Q3: SSH tunnel establishment failed

**A**: Common issues and solutions:
1. **Incorrect private key path**: Ensure the private key file exists and the path is correct
2. **SSH service not running**: Confirm the SSH service on the server is active (port 22)
3. **Password authentication failed**: Try using SSH key authentication, which is more secure
4. **Network issues**: Try manually connecting with the `ssh` command first to confirm the SSH connection works

### Q4: No results returned after sending image

**A**: Check the following points:
1. **Is the ComfyUI workflow correctly configured?** Ensure the receiver node is running
2. **Is the result data block selected?** Confirm an image block for receiving data is selected in Blender
3. **Check Blender system console**: Look for error messages
4. **Are there errors in ComfyUI?** Check ComfyUI's logs/console output

### Q5: Channels not visible after sending multi-channel EXR

**A**: Multi-channel EXR requires a correct receiver node:
1. Ensure the receiver node supports `channel_map`
2. Use a supported receiver node (usually indicated in the node description)
3. Check if the EXR file was generated correctly (you can open it in Blender first to verify)

### Q6: How to stop data transmission?

**A**: Currently, the plugin does not automatically stop after receiving data, but you can:
1. Close Blender or reopen the scene
2. Stop the ComfyUI workflow
3. SSH tunnel will automatically disconnect (if a timeout is set)

## 🎬 Video Tutorials (In Production)

> 📌 **Note**: Detailed installation and usage video tutorials are currently in production. Stay tuned!

### Planned Video Content

1. **Installation Tutorial** - Complete process from download to first use
2. **Basic Workflow Demo** - Demonstrating the complete process from Blender to ComfyUI
3. **SSH Tunnel Configuration** - How to set up remote ComfyUI connection
4. **Multi-Channel EXR Usage** - How to utilize multi-channel render data
5. **Troubleshooting Guide** - Solutions to common issues

### How to Watch

- Videos will be published on [YouTube](https://youtube.com/) and [Bilibili](https://www.bilibili.com/)
- Video links will be added to the "Video Tutorials" section of this README

### Why Video Tutorials?

- Text and image tutorials may not be intuitive enough
- Hands-on demonstrations are easier to understand
- Cover more use cases and edge scenarios

## 💻 Technical Implementation Details (For Node Developers)

This plugin communicates with ComfyUI nodes via ZMQ's `REQ/REP` mode and uses a **Multipart Message** format to send data.

### ZMQ Message Structure

The ZMQ message received by the node contains **2** parts:

1.  **Part 1: Metadata**
    *   **Type**: `msgspec` encoded dictionary (JSON).
    *   **Content**: Contains operation instructions and image information.

2.  **Part 2: Image Binary Data (Image Bytes)**
    *   **Type**: Raw byte stream (`bytes`).
    *   **Content**: Complete binary content of `.png` or `.exr` files.

**The receiver node must use `socket.recv_multipart()` to correctly parse these two parts.**

### Metadata Details

The metadata dictionary contains the following key fields:

*   `render_type` (string):
    *   `'standard'`: Indicates the second part data is a standard **PNG/JPG** image.
    *   `'multilayer_exr'`: Indicates the second part data is a multi-channel **EXR** image.
    *   **The receiver node must determine its processing logic based on this field.**

*   `channel_map` (dictionary):
    *   **Only provided when `render_type` is `'multilayer_exr'`.**
    *   This is a "translation map" used to map ComfyUI's expected channel names (key) to the actual channel names in the EXR file (value).
    *   **Example**: `{'volume_direct': 'ViewLayer.VolumeDir', 'ambient_occlusion': 'ViewLayer.AO'}`.
    *   **When processing EXR, the receiver node must use this map to look up channels, rather than hardcoding channel names.**

## 🤝 Contribution Guide

### How to Contribute?

We welcome contributions of all kinds!

#### 1. Report Bugs 🐛

Found any issues? Please create an [Issue](https://github.com/ageless-h/Blender-ComfyUI-Bridge/issues):
- Describe the issue in detail
- Provide reproduction steps
- Attach relevant logs or screenshots
- Specify your Blender and ComfyUI versions

#### 2. Suggest New Features 💡

Have an idea for a new feature? Please:
- First discuss in [Discussions](https://github.com/ageless-h/Blender-ComfyUI-Bridge/discussions)
- Confirm feature requirements and implementation feasibility
- Create an Issue to track development progress

#### 3. Submit Code PRs 🔀

Ready to contribute code?

1. **Fork** this repository
2
