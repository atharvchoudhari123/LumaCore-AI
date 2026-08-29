import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

OUTPUT = ROOT / "training" / "data" / "prepared.jsonl"


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 training/prepare.py input.jsonl")
        raise SystemExit(1)

    source = Path(sys.argv[1])

    if not source.exists():
        print(f"Input file not found: {source}")
        raise SystemExit(1)

    count = 0

    with source.open("r", encoding="utf-8") as infile:
        with OUTPUT.open("w", encoding="utf-8") as outfile:

            for line in infile:
                if not line.strip():
                    continue

                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue

                messages = item.get("messages")

                if not isinstance(messages, list):
                    continue

                valid = True

                for message in messages:
                    if not isinstance(message, dict):
                        valid = False
                        break

                    if not isinstance(message.get("role"), str):
                        valid = False
                        break

                    if not isinstance(message.get("content"), str):
                        valid = False
                        break

                if not valid:
                    continue

                outfile.write(
                    json.dumps(
                        item,
                        ensure_ascii=False
                    ) + "\n"
                )

                count += 1

    print(f"Prepared {count} examples.")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()
