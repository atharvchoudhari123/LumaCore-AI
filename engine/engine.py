from .context import build_system_prompt, attach_files
from .memory import memory
from .model_registry import get_model, get_checkpoint
from .runtime import runtime


class LumenEngine:
    def complete(
        self,
        model_id,
        messages,
        files=None,
        mode="chat",
        max_new_tokens=512,
        plugins=None,
    ):
        model = get_model(model_id)
        if model is None:
            raise ValueError(f"Unknown Lumen model: {model_id}")

        checkpoint = get_checkpoint(model_id)
        normalized = memory.normalize(messages)
        system = build_system_prompt(model["display_name"], mode)
        normalized = attach_files(normalized, files or [])

        final_messages = [
            {"role": "system", "content": system},
            *normalized,
        ]

        return runtime.generate(
            checkpoint=checkpoint,
            messages=final_messages,
            max_new_tokens=max_new_tokens,
        )


engine = LumenEngine()
