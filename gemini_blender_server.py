# gemini_blender_server.py
# This is the intermediary server that receives HTTP requests from the Gemini agent
# and forwards them as socket commands to the Blender addon.

from flask import Flask, request, jsonify
import socket
import json
import logging
import traceback
import base64
from pathlib import Path
from urllib.parse import urlparse
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GeminiBlenderServer")

app = Flask(__name__)

BLENDER_HOST = 'localhost'
BLENDER_PORT = 9876 # Should match the port in addon.py

def send_to_blender(command):
    """Sends a command to the Blender socket server and returns the response."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(20.0) # Add a timeout
            sock.connect((BLENDER_HOST, BLENDER_PORT))
            sock.sendall(json.dumps(command).encode('utf-8'))
            
            chunks = []
            while True:
                try:
                    chunk = sock.recv(8192)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    # Check if we have received a complete JSON object
                    if b'}' in chunk:
                         # A simple check, might not be robust for all cases
                         # but good enough for this protocol.
                        break
                except socket.timeout:
                    logger.warning("Socket timeout while receiving from Blender.")
                    break
            
            if chunks:
                response_data = b''.join(chunks)
                response = json.loads(response_data.decode('utf-8'))
                logger.info("Received response from Blender.")
                return response
            else:
                logger.error("No response received from Blender.")
                return {"status": "error", "message": "No response from Blender"}
    except ConnectionRefusedError:
        logger.error("Connection to Blender was refused. Is the addon server running?")
        return {"status": "error", "message": "Connection to Blender refused."}
    except Exception as e:
        logger.error(f"Error communicating with Blender: {e}")
        return {"status": "error", "message": str(e)}

# Create a single endpoint to handle all tool calls
@app.route('/run-tool', methods=['POST'])
def run_tool():
    """Generic endpoint to forward tool calls to Blender."""
    data = request.json
    if not data or 'type' not in data:
        return jsonify({"status": "error", "message": "Invalid request format, 'type' is required."}), 400
    
    logger.info(f"Received tool call: {data['type']}")
    
    # Forward the exact JSON command to Blender
    blender_response = send_to_blender(data)
    
    status_code = 500 if blender_response.get("status") == "error" else 200
    return jsonify(blender_response), status_code

if __name__ == '__main__':
    logger.info(f"Starting Gemini-Blender Intermediary Server on http://127.0.0.1:5000")
    logger.info("Ensure the server is started and enabled in Blender.")
    app.run(host='0.0.0.0', port=5000)