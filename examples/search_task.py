"""
Example: Web Search Task

Demonstrates how to use UI-Agent to perform a web search
and extract results.

Run:
    python examples/search_task.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from agent.agent import UIAgent
from agent.config import AgentConfig


async def run_search_example():
    """Search for Python Playwright tutorials and get results."""

    config = AgentConfig(
        llm_provider="openai",
        llm_model="gpt-4o",
        headless=False,
        max_steps=10,
        screenshot_mode=True,
        dom_mode=True,
    )

    agent = UIAgent(config=config)

    task = (
        "Go to https://www.google.com, search for 'Python Playwright tutorial', "
        "find the first organic result, click on it, and tell me the title and "
        "main topic of the page."
    )

    print(f"Task: {task}")
    print("-" * 60)

    result = await agent.run(task)
    print(f"\nResult: {result}")
    return result


if __name__ == "__main__":
    asyncio.run(run_search_example())
