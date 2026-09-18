from .context import build_system_prompt, attach_files
from .memory import memory
from .model_registry import get_model, get_checkpoint, normalize_model_id
from .runtime import runtime


class LumaCoreEngine:
    def complete(
        self,
        model_id,
        messages,
        files=None,
        mode="chat",
        max_new_tokens=512,
        plugins=None,
    ):
        # Accept legacy Lumen IDs while using canonical LumaCore IDs internally.
        canonical_model_id = normalize_model_id(model_id)
        model = get_model(canonical_model_id)

        if model is None:
            raise ValueError(f"Unknown LumaCore model: {model_id}")

        checkpoint = get_checkpoint(canonical_model_id)
        normalized = memory.normalize(messages)

        user_message = ""
        for message in reversed(normalized):
            if message.get("role") == "user":
                user_message = message.get("content", "")
                break

        system = build_system_prompt(
            model["display_name"],
            mode=mode,
            user_message=user_message,
        )

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


engine = LumaCoreEngine()
