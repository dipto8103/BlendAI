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
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
except (AttributeError, KeyError):
    print("ERROR: The GOOGLE_API_KEY environment variable is not set.")
    exit()

SERVER_URL = "http://127.0.0.1:5000/run-tool"

# --- Tool Definitions for Gemini ---
tools_schema = [
    genai.protos.Tool(
        function_declarations=[
            genai.protos.FunctionDeclaration(
                name="execute_blender_code",
                description="Executes a string of Python code directly in Blender's context using the bpy API.",
                parameters=genai.protos.Schema(type=genai.protos.Type.OBJECT, properties={"code": genai.protos.Schema(type=genai.protos.Type.STRING)}, required=["code"])
            ),
            genai.protos.FunctionDeclaration(name="get_scene_info", description="Retrieves information about the current Blender scene."),
            genai.protos.FunctionDeclaration(
                name="get_object_info",
                description="Get detailed information about a specific object by its name.",
                parameters=genai.protos.Schema(type=genai.protos.Type.OBJECT, properties={"object_name": genai.protos.Schema(type=genai.protos.Type.STRING)}, required=["object_name"])
            ),
            genai.protos.FunctionDeclaration(
                name="get_polyhaven_status",
                description="Check if PolyHaven integration is enabled in Blender."
            ),
            genai.protos.FunctionDeclaration(
                name="search_polyhaven_assets",
                description="Search for assets on Polyhaven.",
                 parameters=genai.protos.Schema(type=genai.protos.Type.OBJECT, properties={"asset_type": genai.protos.Schema(type=genai.protos.Type.STRING), "categories": genai.protos.Schema(type=genai.protos.Type.STRING)})
            ),
            genai.protos.FunctionDeclaration(
                name="download_polyhaven_asset",
                description="Download and import a Polyhaven asset.",
                 parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT, 
                    properties={
                        "asset_id": genai.protos.Schema(type=genai.protos.Type.STRING), 
                        "asset_type": genai.protos.Schema(type=genai.protos.Type.STRING), 
                        "resolution": genai.protos.Schema(type=genai.protos.Type.STRING, description="Optional. e.g., '1k', '2k', '4k'.")
                    }, 
                    required=["asset_id", "asset_type"]
                )
            ),
             genai.protos.FunctionDeclaration(
                name="get_hyper3d_status",
                description="Check if Hyper3D Rodin integration is enabled in Blender."
            ),
             genai.protos.FunctionDeclaration(
                name="generate_hyper3d_model_via_text",
                description="Generate a 3D model from a text prompt using Hyper3D.",
                 parameters=genai.protos.Schema(type=genai.protos.Type.OBJECT, properties={"text_prompt": genai.protos.Schema(type=genai.protos.Type.STRING)}, required=["text_prompt"])
            ),
             genai.protos.FunctionDeclaration(
                name="poll_rodin_job_status",
                description="Check the status of a Hyper3D generation task.",
                 parameters=genai.protos.Schema(type=genai.protos.Type.OBJECT, properties={"job_id": genai.protos.Schema(type=genai.protos.Type.STRING)}, required=["job_id"])
            ),
             genai.protos.FunctionDeclaration(
                name="import_generated_asset",
                description="Import a completed Hyper3D asset into Blender.",
                 parameters=genai.protos.Schema(type=genai.protos.Type.OBJECT, properties={"job_id": genai.protos.Schema(type=genai.protos.Type.STRING), "name": genai.protos.Schema(type=genai.protos.Type.STRING)}, required=["job_id", "name"])
            ),
        ]
    )
]

# --- Tool Execution Wrapper ---
def execute_tool_call(tool_name, tool_args):
    """Dispatcher to handle all tool calls by making API requests."""
    print(f"AGENT: Executing tool '{tool_name}' with args {tool_args}")
    try:
        response = requests.post(SERVER_URL, json={"type": tool_name, "params": tool_args})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Agent HTTP Request failed: {e}"}

# --- Main Agent Logic ---
def run_agent(prompt: str, max_turns: int = 15):
    """Runs the main agent loop."""
    system_instruction = """
You are a master 3D artist who controls Blender through a set of tools. Your goal is to fulfill the user's request by breaking it down into a sequence of tool calls.
Think step-by-step. First, analyze the request. If you need to know what's in the scene, use get_scene_info. A standard workflow is to clear the default scene, then add and manipulate objects.
When creating 3D content, prioritize using integrations like Poly Haven or Hyper3D if they are enabled. Only fall back to scripting primitives if necessary.
If a tool call returns an error, analyze the error message and try to correct your approach. Do not repeat the same failed call without modification.
When the request appears to be fulfilled, respond with a confirmation message like 'Task complete.'
"""
    model = genai.GenerativeModel(
        model_name='gemini-2.5-pro-preview-06-05',
        tools=tools_schema,
        system_instruction=system_instruction
    )
    chat = model.start_chat()
    print(f"USER PROMPT: {prompt}")

    # Initial message to kick off the process
    response = chat.send_message(prompt)
    
    turn_count = 0
    while turn_count < max_turns:
        try:
            # Check for function calls in the model's response
            function_calls = response.candidates[0].content.parts[0].function_calls
        except (IndexError, AttributeError, ValueError):
            print(f"GEMINI: {response.text}")
            break
            
        if not function_calls:
            print(f"AGENT: Task complete. Final response: {response.text}")
            break

        print("-" * 20)
        
        # Execute each function call and collect results
        api_responses = []
        for call in function_calls:
            tool_result = execute_tool_call(call.name, dict(call.args))
            api_responses.append(genai.protos.Part(
                function_response=genai.protos.FunctionResponse(name=call.name, response={"content": json.dumps(tool_result)})
            ))

        print("AGENT: Sending tool results back to Gemini...")
        response = chat.send_message(api_responses)
        
        time.sleep(1) # Small delay to observe changes in Blender
        turn_count += 1
    
    if turn_count >= max_turns:
        print("AGENT: Reached maximum turn limit.")
        
    print("AGENT: Finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a Gemini-powered agent to control Blender.")
    parser.add_argument("--prompt", type=str, required=True, help="The high-level prompt for the Blender scene.")
    args = parser.parse_args()
    
    run_agent(args.prompt)