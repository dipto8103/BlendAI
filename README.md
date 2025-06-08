# README.md

# Gemini-Blender Control System (Full-Featured)

This project enables a Gemini-powered AI agent to interact with and control Blender in real-time. It provides a full suite of tools for scene manipulation and asset integration via Poly Haven and Hyper3D.

### System Architecture

The system consists of three main components:

1.  **Blender Addon (`addon.py`):** A self-contained Python script that runs inside Blender. It starts a TCP socket server to listen for JSON-based commands and execute them using Blender's `bpy` API.

2.  **Intermediary Server (`gemini_blender_server.py`):** A Flask web server that acts as a bridge. It exposes a REST API that the Gemini agent calls. The server translates these HTTP requests into socket commands for the Blender addon.

3.  **Gemini Agent (`gemini_blender_agent.py`):** The core agent logic. It uses the Gemini API with function calling to understand a user's prompt, break it down into tool calls, and execute them by sending requests to the intermediary server.

### Setup Instructions

**1. Prerequisites:**
   - Blender 3.0 or newer.
   - Python 3.9 or newer.
   - An active Google Gemini API key.

**2. Python Environment Setup:**
   - It is highly recommended to use a virtual environment.
   - Install the necessary Python libraries:
     ```bash
     pip install google-generativeai flask requests
     ```

**3. Set Gemini API Key:**
   - You must set your Gemini API key as an environment variable.
     - On macOS/Linux: `export GOOGLE_API_KEY='YOUR_API_KEY'`
     - On Windows (Command Prompt): `set GOOGLE_API_KEY=YOUR_API_KEY`
     - On Windows (PowerShell): `$env:GOOGLE_API_KEY='YOUR_API_KEY'`
   - The agent script will read this key from the environment.

**4. Install the Blender Addon:**
   - Save the `addon.py` code below to a file named `addon.py`. **Use the full code provided in this block.**
   - Open Blender.
   - Go to `Edit > Preferences > Add-ons`.
   - Click "Install..." and select the `addon.py` file you just saved.
   - Enable the addon by checking the box next to "Interface: Gemini Blender Control".

### How to Run

The components must be run in the following order:

**Step 1: Start the Blender Connection**
   - In Blender, open the 3D View sidebar (press 'N' if it's not visible).
   - Find the "Gemini Control" tab.
   - Configure integration preferences (Poly Haven, Hyper3D) and provide any necessary API keys.
   - Click the **"Start Server"** button. It will now read "Server Running on Port 9876".
   - Blender is now listening. Leave it running.

**Step 2: Start the Intermediary Server**
   - Save the `gemini_blender_server.py` code below to a file.
   - Open a terminal or command prompt.
   - Navigate to the file's directory and run:
     ```bash
     python gemini_blender_server.py
     ```
   - The Flask server will start on `http://127.0.0.1:5000`.
   - Leave this server running.

**Step 3: Run the Gemini Agent**
   - Save the `gemini_blender_agent.py` code below to a file.
   - Open a **new** terminal or command prompt.
   - Navigate to the file's directory and run the agent with a prompt. Examples:
     ```bash
     # Simple scene creation
     python gemini_blender_agent.py --prompt "Clear the scene. Create a red cube and a blue sphere. Place the sphere 5 units above the cube."

     # Use Poly Haven
     python gemini_blender_agent.py --prompt "Find a 'sunny sky' HDRI from Poly Haven and apply it to the world environment."
     ```
   - Observe the changes happening in your Blender window in real-time.

---