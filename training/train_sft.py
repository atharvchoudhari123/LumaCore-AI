import os
from pathlib import Path

from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments
)
from trl import SFTTrainer


ROOT = Path(__file__).resolve().parents[1]

BASE_MODEL = os.getenv(
    "LUMEN_BASE_MODEL",
    "Qwen/Qwen2.5-0.5B-Instruct"
)

DATASET = (
    ROOT
    / "training"
    / "data"
    / "lumen_train.jsonl"
)

OUTPUT = (
    ROOT
    / "training"
    / "output"
    / "lumen-3.2"
)


def main():

    if not DATASET.exists():
        raise FileNotFoundError(
            f"Training dataset not found: {DATASET}"
        )

    print()
    print("================================")
    print(" LUMEN TRAINING")
    print("================================")
    print()
    print(f"Base model: {BASE_MODEL}")
    print(f"Dataset:    {DATASET}")
    print(f"Output:     {OUTPUT}")
    print()

    dataset = load_dataset(
        "json",
        data_files=str(DATASET),
        split="train"
    )

    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL,
        trust_remote_code=True
    )

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        trust_remote_code=True
    )

    training_args = TrainingArguments(
        output_dir=str(OUTPUT),
        num_train_epochs=1,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=2e-5,
        logging_steps=1,
        save_strategy="epoch",
        report_to="none"
    )

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
        args=training_args
    )

    trainer.train()

    trainer.save_model(
        str(OUTPUT)
    )

    tokenizer.save_pretrained(
        str(OUTPUT)
    )

    print()
    print("Training complete.")
    print(f"Model saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
