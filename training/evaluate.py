import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DATA = (
    ROOT
    / "training"
    / "data"
    / "lumen_train.jsonl"
)


def main():

    if not DATA.exists():
        print(f"Dataset not found: {DATA}")
        return

    total = 0
    valid = 0

    with DATA.open("r", encoding="utf-8") as file:

        for line in file:

            if not line.strip():
                continue

            total += 1

            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            messages = item.get("messages")

            if not isinstance(messages, list):
                continue

            if len(messages) < 2:
                continue

            good = True

            for message in messages:

                if not isinstance(message, dict):
                    good = False
                    break

                if not isinstance(message.get("role"), str):
                    good = False
                    break

                if not isinstance(message.get("content"), str):
                    good = False
                    break

            if good:
                valid += 1

    print(f"Total examples: {total}")
    print(f"Valid examples: {valid}")


if __name__ == "__main__":
    main()
