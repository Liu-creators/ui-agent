"""
Agent Memory - Tracks conversation history and task context
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Step:
    step_num: int
    thought: str
    action: Dict[str, Any]
    observation: str
    screenshot_b64: Optional[str] = None


class AgentMemory:
    """
    Stores the full trace of steps taken by the agent.
    Used to build the conversation history for LLM context.
    """

    def __init__(self, max_history: int = 10):
        self.task: str = ""
        self.steps: List[Step] = []
        self.max_history = max_history  # keep only recent N steps in LLM context

    def set_task(self, task: str):
        self.task = task

    def add_step(self, step: Step):
        self.steps.append(step)

    def get_recent_steps(self) -> List[Step]:
        """Return the most recent steps for LLM context window."""
        return self.steps[-self.max_history:]

    def to_messages(self, include_screenshots: bool = False) -> List[Dict]:
        """
        Convert memory to OpenAI-style messages for LLM input.
        Each step becomes an assistant message (action) + user message (observation).
        """
        messages = []
        for step in self.get_recent_steps():
            # Assistant thought + action
            messages.append({
                "role": "assistant",
                "content": f"Thought: {step.thought}\nAction: {step.action}"
            })
            # Observation
            if include_screenshots and step.screenshot_b64:
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Observation: {step.observation}"},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/png;base64,{step.screenshot_b64}",
                            "detail": "low"
                        }}
                    ]
                })
            else:
                messages.append({
                    "role": "user",
                    "content": f"Observation: {step.observation}"
                })
        return messages

    def summary(self) -> str:
        """Human-readable summary of steps taken."""
        lines = [f"Task: {self.task}"]
        for s in self.steps:
            lines.append(f"Step {s.step_num}: {s.thought} => {s.action}")
        return "\n".join(lines)

    def clear(self):
        self.steps.clear()
