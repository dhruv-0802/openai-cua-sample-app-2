import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.agent import Agent
from computers.default import ScrapybaraBrowser

with ScrapybaraBrowser() as computer:
    agent = Agent(computer=computer)
    input_items = [{"role": "user", "content": "what is the weather in sf"}]
    response_items = agent.run_full_turn(input_items, debug=True, show_images=True)
    print(response_items[-1]["content"][0]["text"])
