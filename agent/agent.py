"""
UI Agent - Core ReAct Loop

Architecture:
  Task --> Planner --> [Thought -> Action -> Observation] loop --> Result

The agent follows the ReAct pattern:
  1. Think: LLM reasons about current state
  2. Act: Execute browser action
  3. Observe: Collect page state (screenshot + DOM)
  4. Repeat until done or max steps reached
"""

import logging
from typing import Any, Dict, Optional

from rich.console import Console
from rich.table import Table
from rich import print as rprint

from agent.config import AgentConfig
from agent.memory import AgentMemory, Step
from browser.browser_env import BrowserEnv
from llm.openai_llm import OpenAILLM
from prompts.system_prompt import get_system_prompt, get_task_prompt

logger = logging.getLogger(__name__)
console = Console()


class UIAgent:
    """
    The main UI Agent that controls a browser to complete tasks.

    Usage:
        agent = UIAgent(config=cfg)
        result = await agent.run("Search for Python tutorials")
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.memory = AgentMemory(max_history=10)
        self.browser = BrowserEnv(
            headless=config.headless,
            timeout=config.browser_timeout,
            slow_mo=config.slow_mo,
            save_screenshots=config.save_screenshots,
            screenshot_dir=config.screenshot_dir,
        )
        self.llm = self._build_llm(config)
        logging.basicConfig(level=getattr(logging, config.log_level, logging.INFO))

    def _build_llm(self, config: AgentConfig) -> OpenAILLM:
        """Initialize the LLM client based on config."""
        base_url = config.openai_base_url
        if config.llm_provider == "deepseek" and not base_url:
            base_url = "https://api.deepseek.com/v1"
        return OpenAILLM(
            model=config.llm_model,
            api_key=config.openai_api_key,
            base_url=base_url,
        )

    async def run(self, task: str) -> str:
        """
        Execute a task using the ReAct loop.

        Args:
            task: Natural language task description

        Returns:
            The final result string from the agent
        """
        self.memory.set_task(task)
        await self.browser.start()

        try:
            result = await self._react_loop(task)
            return result
        finally:
            await self.browser.close()

    async def _react_loop(self, task: str) -> str:
        """Main ReAct loop: Think -> Act -> Observe."""
        step_num = 0
        last_observation = ""

        for step_num in range(1, self.config.max_steps + 1):
            console.rule(f"[bold blue]Step {step_num}/{self.config.max_steps}[/bold blue]")

            # --- Build messages for LLM ---
            messages = self._build_messages(task, step_num, last_observation)

            # --- LLM Thinks and Decides Action ---
            try:
                response = await self.llm.chat(messages)
                thought = response.get("thought", "")
                action = response.get("action", {})
            except Exception as e:
                console.print(f"[red]LLM error: {e}[/red]")
                logger.error(f"LLM error at step {step_num}: {e}")
                continue

            console.print(f"[bold cyan]Thought:[/bold cyan] {thought}")
            console.print(f"[bold yellow]Action:[/bold yellow] {action}")

            # --- Execute Action ---
            action_type = action.get("type", "").lower()

            if action_type == "done":
                result = action.get("result", "Task completed.")
                console.print(f"[bold green]Done:[/bold green] {result}")
                self.memory.add_step(Step(step_num, thought, action, f"Task completed: {result}"))
                return result

            if action_type == "fail":
                reason = action.get("reason", "Unknown failure")
                console.print(f"[bold red]Failed:[/bold red] {reason}")
                return f"Task failed: {reason}"

            observation = await self._execute_action(action_type, action)
            console.print(f"[bold magenta]Observation:[/bold magenta] {observation[:200]}")

            # --- Capture page state ---
            screenshot_b64 = None
            if self.config.screenshot_mode:
                try:
                    screenshot_b64, _ = await self.browser.screenshot()
                    obs_text = f"{observation}\n[Screenshot captured]"
                except Exception:
                    obs_text = observation
            else:
                obs_text = observation

            # DOM info for context
            if self.config.dom_mode and action_type not in ("screenshot", "wait", "scroll"):
                try:
                    dom_text = await self.browser.get_dom_text()
                    obs_text += f"\n\nPage text (truncated): {dom_text[:1000]}"
                except Exception:
                    pass

            # --- Store step in memory ---
            self.memory.add_step(Step(
                step_num=step_num,
                thought=thought,
                action=action,
                observation=obs_text,
                screenshot_b64=screenshot_b64,
            ))
            last_observation = obs_text

        return f"Task incomplete: reached maximum {self.config.max_steps} steps."

    def _build_messages(self, task: str, step_num: int, last_observation: str) -> list:
        """Build the full message list for the LLM."""
        messages = [{"role": "system", "content": get_system_prompt()}]

        # Add history from memory
        history = self.memory.to_messages(
            include_screenshots=self.config.screenshot_mode
        )
        messages.extend(history)

        # Build current step's user message
        if step_num == 1:
            user_content = get_task_prompt(task, step_num, self.config.max_steps)
        else:
            page_info = {}
            user_content = (
                f"Current step: {step_num}/{self.config.max_steps}\n"
                f"Last observation: {last_observation[:500]}\n\n"
                f"Continue with the task. Respond with JSON only."
            )

        # If last step had screenshot, include it as vision
        last_steps = self.memory.get_recent_steps()
        if last_steps and last_steps[-1].screenshot_b64 and self.config.screenshot_mode:
            msg = self.llm.build_vision_message(
                user_content,
                last_steps[-1].screenshot_b64
            )
        else:
            msg = {"role": "user", "content": user_content}

        messages.append(msg)
        return messages

    async def _execute_action(self, action_type: str, action: dict) -> str:
        """Dispatch action to the appropriate browser method."""
        try:
            if action_type == "navigate":
                url = action.get("url", "")
                title = await self.browser.navigate(url)
                return f"Navigated to {url} | Title: {title}"

            elif action_type == "click":
                selector = action.get("selector")
                coordinate = action.get("coordinate")
                return await self.browser.click(selector=selector, coordinate=coordinate)

            elif action_type == "type":
                selector = action.get("selector", "")
                text = action.get("text", "")
                result = await self.browser.type_text(selector, text)
                # Optionally press Enter after typing
                if action.get("press_enter", False):
                    await self.browser.press_key("Enter")
                    result += " + Enter"
                return result

            elif action_type == "scroll":
                direction = action.get("direction", "down")
                amount = int(action.get("amount", 300))
                return await self.browser.scroll(direction, amount)

            elif action_type == "screenshot":
                b64, path = await self.browser.screenshot()
                page_info = await self.browser.get_page_info()
                return f"Screenshot taken | URL: {page_info['url']} | Title: {page_info['title']}"

            elif action_type == "extract":
                selector = action.get("selector")
                text = await self.browser.get_dom_text(selector=selector)
                return f"Extracted text: {text}"

            elif action_type == "wait":
                seconds = float(action.get("seconds", 2))
                return await self.browser.wait(seconds)

            elif action_type == "back":
                return await self.browser.go_back()

            elif action_type == "key":
                key = action.get("key", "Enter")
                return await self.browser.press_key(key)

            else:
                return f"Unknown action type: {action_type}"

        except Exception as e:
            error_msg = f"Action '{action_type}' failed: {str(e)}"
            logger.warning(error_msg)
            return error_msg
