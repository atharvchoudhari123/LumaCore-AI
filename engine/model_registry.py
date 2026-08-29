import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

REGISTRY_FILE = ROOT / "models" / "registry.json"


def get_models():
    data = json.loads(
        REGISTRY_FILE.read_text(
            encoding="utf-8"
        )
    )

    return data["models"]


def get_model(model_id):
    for model in get_models():
        if model["id"] == model_id:
            return model

    return None


def get_checkpoint(model_id):
    model = get_model(model_id)

    if model is None:
        raise ValueError(
            f"Unknown Lumen model: {model_id}"
        )

    variable = model["checkpoint_env"]

    checkpoint = os.getenv(
        variable,
        ""
    ).strip()

    if not checkpoint:
        raise RuntimeError(
            f"{variable} is not configured."
        )

    return checkpoint
