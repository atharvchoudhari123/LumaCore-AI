import os

import anthropic


class AnthropicRuntime:
    """Runtime adapter for Anthropic-hosted LumaCore models."""

    def __init__(self):
        self.client = None

    def _get_client(self):
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not configured. Add your Anthropic API key "
                "to the Codespace environment or .env file."
            )

        if self.client is None:
            self.client = anthropic.Anthropic(api_key=api_key)

        return self.client

    def generate(
        self,
        model,
        messages,
        max_new_tokens=768,
    ):
        client = self._get_client()

        system_messages = [
            message.get("content", "")
            for message in messages
            if message.get("role") == "system"
        ]

        api_messages = [
            {
                "role": message.get("role", "user"),
                "content": message.get("content", ""),
            }
            for message in messages
            if message.get("role") in {"user", "assistant"}
        ]

        if not api_messages:
            raise ValueError("At least one user or assistant message is required.")

        response = client.messages.create(
            model=model,
            max_tokens=max_new_tokens,
            system="\n\n".join(system_messages) if system_messages else None,
            messages=api_messages,
        )

        parts = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)

        return "".join(parts).strip()


anthropic_runtime = AnthropicRuntime()
