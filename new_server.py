


# gemini_blender_agent.py
# The main agent script that uses the Gemini API and its function calling
# capabilities to interact with the intermediary server.

import google.generativeai as genai
import os
import requests
import json
import argparse
import time

# --- Configuration ---
try:
    # Configure the Gemini API client from environment variable
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
except (AttributeError, KeyError):
    print("ERROR: The GOOGLE_API_KEY environment variable is not set.")
    print("Please set your API key to run the agent.")
    exit()

# URL of the intermediary Flask server
SERVER_URL = "http://127.0.0.1:5000/run-tool"

# --- Tool Definitions for Gemini ---
# These function definitions will be provided to the Gemini model.
# They serve as a schema for the tool calls it can make.
# The actual implementation is handled by the wrapper functions below.

tools_schema = [
    {
        "name": "execute_blender_code",
        "description": "Executes a string of Python code directly in Blender's context. Use this for creating objects, transformations, setting materials, etc. The code must use Blender's Python API (bpy).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "code": {"type": "STRING", "description": "A string containing the Python code to execute in Blender."}
            },
            "required": ["code"]
        }
    },
    {
        "name": "get_scene_info",
        "description": "Retrieves general information about the current Blender scene, such as the number of objects and their names.",
        "parameters": {}
    },
    {
        "name": "get_object_info",
        "description": "Get detailed information about a specific object in the Blender scene.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "object_name": {"type": "STRING", "description": "The name of the object to get information about."}
            },
            "required": ["object_name"]
        }
    },
    {
        "name": "search_polyhaven_assets",
        "description": "Search for assets on Polyhaven with optional filtering. Returns a list of matching assets with basic information.",
         "parameters": {
            "type": "OBJECT",
            "properties": {
                "asset_type": {"type": "STRING", "description": "Type of assets (hdris, textures, models, all).", "default": "all"},
                "categories": {"type": "STRING", "description": "Optional comma-separated list of categories to filter by."}
            },
        }
    },
    {
        "name": "download_polyhaven_asset",
        "description": "Download and import a Polyhaven asset into Blender.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "asset_id": {"type": "STRING", "description": "The ID of the asset to download."},
                "asset_type": {"type": "STRING", "description": "The type of asset (hdris, textures, models)."},
                "resolution": {"type": "STRING", "description": "The resolution to download (e.g., 1k, 2k, 4k).", "default": "1k"},
            },
            "required": ["asset_id", "asset_type"]
        }
    },
    {
        "name": "generate_hyper3d_model_via_text",
        "description": "Generate 3D asset using Hyper3D from a text description and import it into Blender. The generated model has a normalized size, so re-scaling after generation can be useful.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "text_prompt": {"type": "STRING", "description": "A short description of the desired model in English."},
            },
            "required": ["text_prompt"]
        }
    }
    # Add other tool schemas here for full functionality...
]


# --- Tool Execution Wrapper ---
# This function acts as a dispatcher. When Gemini returns a function_call,
# this dispatcher will execute it by sending a request to our server.

def execute_tool_call(tool_name, tool_args):
    """A single function to handle all tool calls by making API requests."""
    print(f"AGENT: Executing tool '{tool_name}' with args {tool_args}")
    try:
        response = requests.post(SERVER_URL, json={
            "type": tool_name,
            "params": tool_args
        })
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Agent HTTP Request failed: {e}"}

# --- Main Agent Logic ---

def run_agent(prompt: str, max_turns: int = 15):
    """Runs the main agent loop."""
    
    # System prompt to guide the model's behavior
    system_instruction = """
You are a master 3D artist who controls Blender through a set of tools.
Your goal is to fulfill the user's request by breaking it down into a series of tool calls.
Think step-by-step. First, analyze the request. If you need to know what's in the scene, use get_scene_info.
A standard workflow is to clear the default scene, then add and manipulate objects.
When creating 3D content, always start by checking if integrations are available.
When using tools that might take time, like generating a model, inform the user about what you are doing.
If a tool call returns an error, analyze the error message and try to correct your approach in the next step. Do not repeat the same failed call without modification.
When the request is fulfilled, respond with a confirmation message like 'Task complete.'
"""

    model = genai.GenerativeModel(
        model_name='gemini-1.5-pro-latest',
        tools=tools_schema,
        system_instruction=system_instruction
    )

    chat = model.start_chat()
    print(f"USER PROMPT: {prompt}")

    # Initial message to kick off the process
    response = chat.send_message(prompt)
    
    turn_count = 0
    while turn_count < max_turns:
        # Check for function calls in the model's response
        try:
            function_calls = response.candidates[0].content.parts[0].function_calls
        except (IndexError, AttributeError):
            # No function calls, the model might have finished or is just talking.
            print(f"GEMINI: {response.text}")
            break
            
        if not function_calls:
            print("AGENT: Task complete or model did not request further actions.")
            print(f"GEMINI: {response.text}")
            break

        print("-" * 20)
        
        # Execute each function call
        api_responses = []
        for call in function_calls:
            tool_name = call.name
            tool_args = {key: value for key, value in call.args.items()}
            
            # Execute the tool and get the result
            api_response = execute_tool_call(tool_name, tool_args)
            
            # Append the result for the next turn
            api_responses.append({
                "function_name": tool_name,
                "response": {"content": json.dumps(api_response)}
            })

        # Send the tool execution results back to the model
        print("AGENT: Sending tool results back to Gemini...")
        response = chat.send_message(
            genai.Part(function_response=genai.protos.FunctionResponse(
                name=function_calls[0].name, # In multi-call scenarios, this might need adjustment
                response={"content": json.dumps(api_responses)}
            ))
        )
        
        time.sleep(1) # Small delay to observe changes
        turn_count += 1
    
    if turn_count >= max_turns:
        print("AGENT: Reached maximum turn limit.")
        
    print("AGENT: Finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a Gemini-powered agent to control Blender.")
    parser.add_argument("--prompt", type=str, required=True, help="The high-level prompt for the Blender scene.")
    args = parser.parse_args()
    
    run_agent(args.prompt)
