import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REGISTRY_FILE = ROOT / "models" / "registry.json"

DEFAULT_CHECKPOINT = "Qwen/Qwen2.5-0.5B-Instruct"


def normalize_model_id(model_id):
    """Normalize legacy Lumen IDs to canonical LumaCore IDs."""
    value = (model_id or "").strip().lower()

    if value.startswith("lumen-"):
        return "lumacore-" + value[len("lumen-"):]

    return value


def get_models():
    if not REGISTRY_FILE.exists():
        return [
            {
                "id": "lumacore-3.2",
                "display_name": "LumaCore 3.2",
                "tier": "fast",
                "checkpoint_env": "LUMACORE_3_2_CHECKPOINT",
            },
            {
                "id": "lumacore-4.0",
                "display_name": "LumaCore 4.0",
                "tier": "general",
                "checkpoint_env": "LUMACORE_4_0_CHECKPOINT",
            },
            {
                "id": "lumacore-5.7",
                "display_name": "LumaCore 5.7",
                "tier": "advanced",
                "checkpoint_env": "LUMACORE_5_7_CHECKPOINT",
            },
        ]

    data = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    return data.get("models", [])


def get_model(model_id):
    canonical = normalize_model_id(model_id)

    for model in get_models():
        if model["id"] == canonical:
            return model

    return None


def get_checkpoint(model_id):
    model = get_model(model_id)

    if model is None:
        raise ValueError(
            f"Unknown LumaCore model: {model_id}"
        )

    env_name = model.get("checkpoint_env", "")
    checkpoint = os.getenv(env_name, "").strip()

    if checkpoint:
        return checkpoint

    return DEFAULT_CHECKPOINT
