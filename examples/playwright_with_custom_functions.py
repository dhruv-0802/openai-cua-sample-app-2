import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.agent import Agent
from computers.default import LocalPlaywrightBrowser
from computers.default import ScrapybaraBrowser
from computers.contrib import HyperbrowserBrowser
from google import genai
from pydantic import BaseModel, Field
import json
tools = [
    {
        "type": "function",
        "name": "goto",
        "description": "Go to a specific URL.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Fully qualified URL to navigate to. include the http or https",
                },
            },
            "additionalProperties": False,
            "required": ["url"],
        },
    
    },
]

def auto_approve_safety_check(message):
    print(message)
    return True

class TaskValidator(BaseModel):
    task_completed: bool = Field(description="True if the task has been completed, False otherwise")
    reason: str = Field(description="Reason for the task completion or failure")

def validator_gemini(last_message, agent_message_list, screenshot, user_task):
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    model_flash = "gemini-2.5-flash-preview-05-20"
    system_prompt = """
    system_prompt:
    Context:
    Ripplica is a computer use agent, trying to complete a task given by the user by automating the browser by controlling the mouse and keyboard and using functions to switch tabs and navigating to urls.
    Your Role:
    You are an external evaluator , you are being called when the agent has paused and trying to determine if the user should provide agent with more information 
    or the agent should end the task. There are 2 possible conditions when to end the task, when the agent has tried everything and still not able to complete the task , this is task completed and failed
    and when the agent has successfully completed the task
    or there could be a scenario where agent is asking for more information from the user, examples are login credentials, help from user to take over and complete an action which it is not capable of doing and confirmation before
    any sensitive action
    Inputs:
    To make effective judgement you are provided with the latest message by the agent , a list of messages from the agent and the latest screenshot of the state of agent and the initial task which the user wanted to get done
    Your output:
    If you feel that the task has been ended return True with a reason 
    If you feel the task must go on return False with a reason
    """
    
    # Handle None values and create proper content structure
    user_task = user_task or "No specific task provided"
    last_message = last_message or "No message available"
    
    # Create a properly structured prompt
    prompt = f"{system_prompt}\n\nUser Task: {user_task}\nLatest Agent Message: {last_message}\nAgent Message History: {str(agent_message_list)}"
    if screenshot:
        prompt += f"\nScreenshot Status: Screenshot available"
    else:
        prompt += f"\nScreenshot Status: No screenshot available"

    
    try:
        response = client.models.generate_content(
            model=model_flash,
            contents=prompt,
            config={
                'temperature': 0,
                'response_mime_type': "application/json",
                'response_schema': TaskValidator
            }
        )
        response_json= json.loads(response.text)
        print(response_json)
        return response_json
    except Exception as e:
        print(f"Error: {e}")
        return "Error"

def main():
    with HyperbrowserBrowser() as computer:
        agent = Agent(computer=computer, tools=tools,acknowledge_safety_check_callback=auto_approve_safety_check)
        items=[]
        
        items = [
            {
                "role": "developer",
                "content": "Use the additional goto() to go to a specific url everytime you need to go to a new url or open a new tab or go to url in new tab,  dont use click and type for these actions",
            }
        ]
        user_input = open("examples/user_input7.txt", "r").read()
        
        items.append({"role": "user", "content": user_input})
        items.append({
            "role": "system", 
            "content": """
                Perform tasks using available information and tools.
                
                If at some point additional information or confirmation is needed, 
                or there is a task like a CAPTCHA solving which requires user assistance,
                communicate this clearly using assistant message.
                
                Provide updates and ask for input appropriately by assuming the role of assistant.
                
                If you see nothing, try going to google.com.

                To navigate to any url strictly use the goto() function and nothing else
            """
        })
        while True:
            user_input = input(">>>>>")
            items.append({"role": "user", "content": user_input})
            
            
            # Add retry logic
            max_retries = 5
            retry_count = 0
            while retry_count < max_retries:
                try:
                    output_items, agent_message_list, latest_screenshot = agent.run_full_turn(items, show_images=False)
                    break  # If successful, break out of retry loop
                except ValueError as e:
                    if str(e) == "No output from model":
                        retry_count += 1
                        print(f"Attempt {retry_count}/{max_retries}: No output from model, retrying...")
                        if retry_count == max_retries:
                            print("Maximum retries reached. Please try again later.")
                            return
                        continue
                    else:
                        raise  # Re-raise if it's a different ValueError
            
            items += output_items
            print("shalalalalla--------------------------")
            latest_screenshot = latest_screenshot
            last_message = agent_message_list[-1]
            print("user task is =------------------------------")
            #print(items[1]["content"][0]["text"]) 
            print(items[1]["content"])
            user_task = items[1]["content"]
            print("agent latest message is -------------------------------")
            print(last_message)
            status = validator_gemini(last_message, agent_message_list, latest_screenshot, user_task)
            print(status)


if __name__ == "__main__":
    main()
