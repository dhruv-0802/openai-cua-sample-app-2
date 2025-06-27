from computers import Computer
from utils import (
    create_response,
    show_image,
    pp,
    sanitize_message,
    check_blocklisted_url,
)
import json
from typing import Callable
from google import genai 
import time



class Agent:
    """
    A sample agent class that can be used to interact with a computer.

    (See simple_cua_loop.py for a simple example without an agent.)
    """

    def __init__(
        self,
        model="computer-use-preview-2025-03-11",
        computer: Computer = None,
        tools: list[dict] = [],
        acknowledge_safety_check_callback: Callable = None
    ):
        self.model = model
        self.computer = computer
        self.tools = tools
        self.print_steps = True
        self.debug = True
        self.show_images = False
        self.acknowledge_safety_check_callback = acknowledge_safety_check_callback
        self.agent_message_list = []
        self.latest_screenshot = None
        self.user_task=""

        if computer:
            dimensions = computer.get_dimensions()
            self.tools += [
                {
                    "type": "computer-preview",
                    "display_width": dimensions[0],
                    "display_height": dimensions[1],
                    "environment": computer.get_environment(),
                },
            ]

    def debug_print(self, *args):
        if self.debug:
            pp(*args)
            with open('output.txt', 'a') as f:
                f.write(f"Debug Output:\n{json.dumps(args, indent=4)}\n\n")

    def handle_item(self, item, user_task):
        """Handle each item; may cause a computer action + screenshot."""
        if item["type"] == "message":
            print(item["content"][0]["text"], flush=True)
            self.agent_message_list.append(item["content"][0]["text"])
            return []  # Return empty list for message items
            #return []  # Return empty list for message items

        if item["type"] == "reasoning":
            # Handle reasoning items (AI's internal thinking)
            if self.debug:
                print(f"Reasoning: {item.get('summary', 'No summary')}")
                print(item["summary"][0]["text"], flush=True)
                self.agent_message_list.append(item["summary"][0]["text"])
            return []  # Return empty list for reasoning items

        if item["type"] == "function_call":
            name, args = item["name"], json.loads(item["arguments"])
            if self.print_steps:
                print(f"{name}({args})")
                self.agent_message_list.append(f"{name}({args})")
                self.latest_screenshot = self.computer.screenshot()

            if hasattr(self.computer, name):  # if function exists on computer, call it
                method = getattr(self.computer, name)
                try:
                    method(**args)
                    output = "success"
                except Exception as e:
                    output = f"error: {str(e)}"
                    if self.debug:
                        print(f"Error executing {name}({args}): {e}")
            else:
                output = f"error: method '{name}' not found on computer"
                if self.debug:
                    print(f"Method '{name}' not found on computer object")
                    
            return [
                {
                    "type": "function_call_output",
                    "call_id": item["call_id"],
                    "output": "success",  # hard-coded output for demo
                }
            ]

        if item["type"] == "computer_call":
            action = item["action"]
            action_type = action["type"]
            action_args = {k: v for k, v in action.items() if k != "type"}
            if self.print_steps:
                print(f"{action_type}({action_args})")
                self.agent_message_list.append(f"{action_type}({action_args})")
                self.latest_screenshot = self.computer.screenshot()

            # Add retry mechanism for all errors
            max_retries = 5
            retry_count = 0
            last_error = None
            
            while retry_count < max_retries:
                try:
                    method = getattr(self.computer, action_type)
                    method(**action_args)
                    break  # If successful, exit the retry loop
                except Exception as e:  # Catch all errors
                    retry_count += 1
                    last_error = e
                    print("we have a error bitches!!")
                    print(f"Error: {e}")
                    if self.debug:
                        print(f"Attempt {retry_count}/{max_retries}: Error executing '{action_type}': {e}")
                    if retry_count < max_retries:
                        time.sleep(1)  # Simple 1-second delay between retries
                        continue

            if retry_count == max_retries:
                error_msg = f"Failed to execute {action_type} after {max_retries} attempts. Last error: {last_error}"
                if self.debug:
                    print(error_msg)
                raise RuntimeError(error_msg)

            screenshot_base64 = self.computer.screenshot()
            if self.show_images:
                show_image(screenshot_base64)

            # if user doesn't ack all safety checks exit with error
            pending_checks = item.get("pending_safety_checks", [])
            for check in pending_checks:
                message = check["message"]
                if not self.acknowledge_safety_check_callback(message):
                    raise ValueError(
                        f"Safety check failed: {message}. Cannot continue with unacknowledged safety checks."
                    )

            call_output = {
                "type": "computer_call_output",
                "call_id": item["call_id"],
                "acknowledged_safety_checks": pending_checks,
                "output": {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{screenshot_base64}",
                },
            }

            # additional URL safety checks for browser environments
            if self.computer.get_environment() == "browser":
                current_url = self.computer.get_current_url()
                check_blocklisted_url(current_url)
                #current_url = "www.google.com"
                call_output["output"]["current_url"] = current_url

            result = [
                call_output
                # {
                #     "role": "user", 
                #     "content": "Please analyze if the current task is complete and provide a detailed assessment."
                # }
            ]
            if self.debug:
                #print(f"Returning from handle_item: {result}")
                pass
            return result

    def run_full_turn(
        self, input_items, print_steps=True, debug=False, show_images=False
    ):
        self.print_steps = print_steps
        self.debug = debug
        self.show_images = show_images
        new_items = []
        self.user_task=input_items[0]["content"]
        status=[]
        # keep looping until we get a final response
        while new_items[-1].get("role") != "assistant" if new_items else True:
            self.debug_print([sanitize_message(msg) for msg in input_items + new_items])
            # with open('output.txt', 'a') as f:
            #     f.write(f"Input Items:\n{json.dumps(self.debug_print([sanitize_message(msg) for msg in input_items + new_items]), indent=4)}\n\n")

            max_retries = 5
            retry_count = 0
            while retry_count < max_retries:
                try:
                    response = create_response(
                        model=self.model,
                        input=input_items + new_items,
                        tools=self.tools,
                        truncation="auto",
                        reasoning={
                            "summary": "concise"
                        }
                    )
                    # Check if response has output, if not treat as an error
                    if "output" not in response:
                        raise ValueError(f"No output in response: {response}")
                    break
                except Exception as e:
                    retry_count += 1
                    print(f"Create Response Attempt {retry_count}/{max_retries}: Error occurred, retrying... ({str(e)})")
                    if retry_count == max_retries:
                        print("Create Response: Maximum retries reached.")
                        raise  # Re-raise the last exception if all retries fail
                    time.sleep(1)  # Add a small delay between retries

            if "output" not in response and self.debug:
                #print(response)
                raise ValueError("No output from model")
            # elif new_items and new_items[-1].get("role") == "assistant":
            #     status = validate_gemini(new_items[-1]["content"][0]["text"], self.computer.screenshot(), self.user_task)
            #     if status == "task_completed":
            #         break
            else:
                new_items += response["output"]
                for item in response["output"]:
                    new_items += self.handle_item(item, self.user_task)
                    agent_message_list = self.agent_message_list
                    print(agent_message_list)
                    latest_screenshot = self.latest_screenshot
                    

        return new_items, agent_message_list, latest_screenshot
