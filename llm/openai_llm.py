"""
OpenAI / DeepSeek LLM Client

Supports:
  - OpenAI GPT-4o, GPT-4-turbo, GPT-3.5-turbo
  - DeepSeek (via OpenAI-compatible API)
  - Vision input (base64 screenshot)
"""

import json
import logging
import re
from typing import List, Dict, Optional, Any

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class OpenAILLM:
    """
    Async LLM client supporting OpenAI and DeepSeek.
    Handles retries, JSON parsing, and vision input.
    """

    PROVIDER_ENDPOINTS = {
        "openai": None,  # uses default
        "deepseek": "https://api.deepseek.com/v1",
    }

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        response_format: str = "json",
    ) -> Dict[str, Any]:
        """
        Send messages to the LLM and parse the JSON response.

        Args:
            messages: List of {role, content} dicts
            response_format: 'json' to force JSON output

        Returns:
            Parsed dict with 'thought' and 'action' keys
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        # Use JSON mode if supported (GPT-4o, GPT-4-turbo)
        if response_format == "json" and "gpt" in self.model:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self.client.chat.completions.create(**kwargs)
        raw = response.choices[0].message.content.strip()
        logger.debug(f"LLM raw response: {raw[:500]}")

        return self._parse_json_response(raw)

    def _parse_json_response(self, raw: str) -> Dict[str, Any]:
        """
        Robustly parse JSON from LLM output.
        Handles markdown code blocks and extra text.
        """
        # Try direct parse first
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        patterns = [
            r"```json\s*([\s\S]*?)```",  # ```json ... ```
            r"```\s*([\s\S]*?)```",       # ``` ... ```
            r"\{[\s\S]*\}",               # { ... } (first JSON object)
        ]
        for pattern in patterns:
            match = re.search(pattern, raw)
            if match:
                try:
                    candidate = match.group(1) if pattern != r"\{[\s\S]*\}" else match.group(0)
                    return json.loads(candidate.strip())
                except json.JSONDecodeError:
                    continue

        raise ValueError(f"Failed to parse JSON from LLM response:\n{raw[:500]}")

    def build_vision_message(self, text: str, screenshot_b64: str) -> Dict:
        """
        Build a user message with both text and screenshot image.
        """
        return {
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{screenshot_b64}",
                        "detail": "low",  # 'low' is cheaper, 'high' for more detail
                    },
                },
            ],
        }
