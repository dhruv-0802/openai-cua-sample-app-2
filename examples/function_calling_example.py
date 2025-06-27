import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.agent import Agent
from computers.contrib import HyperbrowserBrowser
from google import genai


tools = [
    {
        "type": "function",
        "name": "get_weather",
        "description": "Determine weather in my location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state e.g. San Francisco, CA",
                },
                "unit": {"type": "string", "enum": ["c", "f"]},
            },
            "additionalProperties": False,
            "required": ["location", "unit"],
        },
    }
]


def main():
    with HyperbrowserBrowser() as computer:
        agent = Agent(tools=tools, computer=computer)
        items = []
        while True:
            user_input = input("> ")
            items.append({"role": "user", "content": user_input})
            output_items = agent.run_full_turn(items)
            items += output_items


if __name__ == "__main__":
    main()
