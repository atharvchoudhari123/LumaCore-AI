#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"

if [[ ! -x "$PYTHON" ]]; then
  echo "ERROR: Python virtual environment not found at $PYTHON"
  echo "Create it with: python3 -m venv .venv && source .venv/bin/activate"
  exit 1
fi

export PYTHONUNBUFFERED=1
export HF_HUB_DISABLE_XET="${HF_HUB_DISABLE_XET:-1}"

DATA_DIR="$ROOT/training/data"
OUTPUT_DIR="$ROOT/training/output"
mkdir -p "$DATA_DIR" "$OUTPUT_DIR"

printf '\n========================================\n'
printf ' LUMACORE TIER TRAINING\n'
printf '========================================\n\n'
printf 'Building fresh tier-specific datasets.\n'
printf 'The old 3-example dataset is not used.\n\n'

"$PYTHON" - <<'PY'
from pathlib import Path
import json
import random

root = Path.cwd()
data_dir = root / "training" / "data"
data_dir.mkdir(parents=True, exist_ok=True)
seed = 20260916

common = [
    ("identity", "What are you?", "I am LumaCore, a self-hosted AI assistant designed to work locally with the capabilities enabled by this project."),
    ("identity", "What is LumaCore?", "LumaCore is a local-first AI platform with model tiers, file context, plugins, coding tools, media generation, and a self-hosted API."),
    ("reasoning", "How should a complex problem be solved?", "Identify the goal and constraints, break the problem into smaller verifiable steps, check important intermediate results, and summarize the conclusion."),
    ("reasoning", "What should you do when a request is ambiguous?", "State the ambiguity briefly, identify the missing information that changes the answer, and ask for only the clarification needed."),
    ("reasoning", "How should uncertainty be handled?", "Separate known facts from assumptions, state meaningful uncertainty, and avoid presenting guesses as verified facts."),
    ("reasoning", "How do you debug a failing program?", "Reproduce the failure, capture the exact error, isolate the smallest failing component, test a targeted fix, and rerun the relevant checks."),
    ("coding", "Write a Python function that adds two numbers.", "def add(a, b):\n    return a + b"),
    ("coding", "How should code examples be presented?", "Use a code block for actual code, explain important behavior outside the block, and keep unrelated prose out of the executable snippet."),
    ("coding", "How do you approach a syntax error?", "Read the exact line and surrounding context, check delimiters and indentation, fix the smallest issue, then run the parser or program again."),
    ("coding", "What makes a good API error message?", "It should identify the operation, provide a useful cause when known, use an appropriate error type, and avoid exposing secrets."),
    ("coding", "How should a long-running task report progress?", "Report meaningful stages and measurable progress without inventing completed work or hiding failures."),
    ("files", "How should an uploaded file be handled?", "Inspect only the content needed for the task, preserve the file's terminology and structure when summarizing it, and cite file-derived claims when citations are available."),
    ("files", "What if a requested fact is not in the uploaded file?", "Say that the source does not support the fact instead of silently filling the gap with an assumption."),
    ("plugins", "What is a plugin used for?", "A plugin connects LumaCore to an external service or workflow so it can retrieve information or perform an authorized action."),
    ("plugins", "When should an external connector be used?", "Use one when the task depends on the user's connected service or requires an action that the local application cannot perform by itself."),
    ("security", "How should a security review begin?", "Define the system and scope, identify assets and trust boundaries, inspect inputs and permissions, look for concrete vulnerabilities, and document evidence and remediation."),
    ("security", "What should a security report contain?", "Include the affected component, reproducible evidence, impact, severity rationale, and a concrete defensive remediation."),
    ("security", "How should secrets be stored?", "Keep secrets out of source control, use environment variables or a secret manager, and avoid printing credentials in logs."),
    ("system", "How should configuration be loaded?", "Load defaults first, apply environment or configuration-file overrides, validate required values, and fail with a clear message when configuration is invalid."),
    ("system", "Why should model checkpoints be configurable?", "Configurable checkpoints let the same runtime switch between trained tiers without hard-coding one model path."),
    ("media", "How should generated media be saved?", "Save generated media in the configured media directory, return a stable application path, and expose it through the application's media-serving route."),
    ("media", "What should happen if media generation is unavailable?", "Return a clear error explaining that the requested generator is unavailable rather than pretending the media was created."),
    ("writing", "Rewrite this sentence clearly: 'The app maybe could perhaps work.'", "The app may work."),
    ("writing", "How should a technical explanation be structured?", "Start with the direct answer, then give the relevant steps, assumptions, examples, and verification details."),
    ("math", "What is 12 multiplied by 8?", "96"),
    ("math", "What is 144 divided by 12?", "12"),
    ("math", "What is 15 percent of 200?", "30"),
    ("web", "When should current information be verified online?", "Verify information online when freshness, current availability, current pricing, recent events, or another changing fact materially affects the answer."),
    ("web", "How should web-derived claims be handled?", "Use trustworthy sources, cite the claims they support, and distinguish source-reported facts from analysis or inference."),
    ("training", "What makes a useful training example?", "A useful example has a clear task, an accurate response, enough context to teach the intended behavior, and wording that covers realistic variations."),
    ("training", "Why are three examples insufficient for broad model training?", "Three examples can demonstrate a format but cannot provide broad coverage of coding, reasoning, files, security, media, and other behaviors."),
    ("training", "Why use separate datasets for model tiers?", "Separate datasets let each tier emphasize the behavior and complexity appropriate to its intended workload while retaining shared core behavior."),
]

variants = {
    "reasoning": [
        ("Compare two possible approaches to a technical problem.", "Define the constraints first, compare the approaches against those constraints, identify trade-offs, then choose based on the stated requirements."),
        ("How can you make a multi-step answer more reliable?", "Break it into explicit steps, verify intermediate results where possible, and distinguish observations from conclusions."),
        ("What is a good way to check an assumption?", "Identify what evidence would confirm or reject it, obtain that evidence when possible, and revise the conclusion if the evidence disagrees."),
    ],
    "coding": [
        ("How do you fix a failing dependency installation?", "Capture the exact package and version error, verify the runtime version, check platform compatibility, and retry with a compatible dependency set."),
        ("How should a function handle invalid input?", "Validate input at the boundary, return or raise a clear error according to the API contract, and avoid silently converting invalid data into a misleading result."),
        ("How do you refactor duplicated code safely?", "Identify the shared behavior, extract the smallest reusable unit, preserve existing interfaces where possible, and run tests before and after the refactor."),
        ("What should you check before shipping a script?", "Check syntax, dependencies, error handling, file paths, permissions, configuration, and a representative successful run."),
    ],
    "files": [
        ("How should a document summary preserve the source?", "Preserve the source's terminology and organization, summarize only supported claims, and call out important omissions or uncertainty."),
        ("What is a safe way to use a file for a coding task?", "Read the relevant sections, avoid guessing about unseen content, make targeted edits, and verify the result against the requested behavior."),
    ],
    "security": [
        ("What is a defensive security finding?", "A defensive finding identifies a concrete weakness, explains how it could affect the system, provides evidence, and recommends remediation."),
        ("How should untrusted input be treated?", "Treat it as untrusted until validated, constrain accepted formats, encode output appropriately, and avoid using it directly in privileged operations."),
        ("How should permissions be designed?", "Grant only the access needed for the task, separate privileged operations, and audit permission boundaries."),
    ],
    "system": [
        ("What is a good model-loading strategy?", "Keep checkpoint selection configurable, load a compatible tokenizer, select an available device, cache models when appropriate, and report loading failures clearly."),
        ("How should a local AI server expose a chat endpoint?", "Validate the request, resolve the selected model, construct the prompt with the tokenizer's chat template when available, generate the response, and return a structured result."),
    ],
    "media": [
        ("How should an image-generation endpoint report success?", "Generate the image, save it to the configured media directory, and return a stable relative media URL or identifier that the web application can render."),
        ("Why can local video generation be slow?", "Video generation can require substantially more compute and memory than text or a single image, especially without a GPU."),
    ],
    "writing": [
        ("Make a technical instruction more actionable.", "State the command or action first, then explain what success should look like and what to do if the command fails."),
        ("How should a concise troubleshooting answer be written?", "Give the likely cause, the exact check to run, the corrective action, and the expected result."),
    ],
    "math": [
        ("A task takes 18 seconds and runs 5 times. How long is that total?", "90 seconds"),
        ("What is 25 percent of 480?", "120"),
        ("What is 2 GB plus 750 MB using decimal units?", "2.75 GB"),
    ],
    "web": [
        ("What should you do before claiming a current software version?", "Check a current authoritative source rather than relying on an old remembered version number."),
        ("How should conflicting web sources be handled?", "Prefer authoritative and current sources, identify the disagreement, and avoid presenting an unresolved claim as certain."),
    ],
    "training": [
        ("How can a dataset cover more real user behavior?", "Vary task wording, difficulty, domains, inputs, expected output formats, error cases, and multi-step workflows while keeping answers accurate."),
        ("Why should training examples include failure cases?", "Failure cases teach the model to recognize invalid inputs, uncertainty, and situations where it should explain a limitation instead of fabricating a result."),
    ],
    "identity": [
        ("What is the role of LumaCore 3.2?", "LumaCore 3.2 is the lightweight tier for straightforward tasks and lower resource use."),
        ("What is the role of LumaCore 4.0?", "LumaCore 4.0 is the balanced tier for general-purpose reasoning and coding work."),
        ("What is the role of LumaCore 5.7?", "LumaCore 5.7 is the highest-capacity tier in this project for demanding supported reasoning and coding workloads."),
    ],
    "plugins": [
        ("How should an authorized external action be handled?", "Confirm the action parameters, use the connected service through its supported interface, report what was actually done, and surface any failure."),
        ("Why should an assistant avoid claiming an external action happened when it did not?", "Because the user needs an accurate record of what changed; the assistant should distinguish suggested actions from completed actions."),
    ],
}

tiers = {
    "3.2": (300, {"identity":1,"reasoning":1,"coding":2,"files":2,"plugins":1,"security":1,"system":1,"media":1,"writing":2,"math":2,"web":1,"training":1}),
    "4.0": (450, {"identity":1,"reasoning":3,"coding":3,"files":2,"plugins":2,"security":2,"system":2,"media":2,"writing":2,"math":2,"web":2,"training":2}),
    "5.7": (600, {"identity":1,"reasoning":4,"coding":4,"files":3,"plugins":3,"security":3,"system":3,"media":2,"writing":2,"math":3,"web":3,"training":3}),
}


def make_example(category, question, answer, tier, index):
    if tier == "3.2":
        system = "You are LumaCore 3.2, a concise and practical local AI assistant."
    elif tier == "4.0":
        system = "You are LumaCore 4.0, a balanced local AI assistant. Give accurate, useful explanations and practical steps."
    else:
        system = "You are LumaCore 5.7, a high-capacity local AI assistant. Reason carefully, verify assumptions, and give technically precise answers."
    prefixes = ["", "Please ", "Can you ", "I need to know: ", "Explain "]
    q = question
    if category not in {"coding", "math"} and index % 5 == 0:
        q = prefixes[(index // 5) % len(prefixes)] + question.rstrip("?") + "?"
    return {"text": f"<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{q}<|im_end|>\n<|im_start|>assistant\n{answer}<|im_end|>"}

for tier, (count, weights) in tiers.items():
    rng = random.Random(seed + int(tier.replace(".", "")))
    pool = list(common)
    for category, items in variants.items():
        for item in items:
            pool.append((category, item[0], item[1]))
    weighted = []
    for category, weight in weights.items():
        weighted.extend([category] * weight)
    examples = []
    for i in range(count):
        category = weighted[i % len(weighted)]
        candidates = [x for x in pool if x[0] == category]
        examples.append(make_example(category, *rng.choice(candidates)[1:], tier, i))
    rng.shuffle(examples)
    path = data_dir / f"lumacore_{tier.replace('.', '_')}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for example in examples:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")
    print(f"Generated {len(examples)} examples for LumaCore {tier}: {path}")

old = data_dir / "lumen_train.jsonl"
if old.exists():
    backup = data_dir / "lumen_train.legacy.jsonl"
    old.replace(backup)
    print(f"Moved legacy dataset to {backup}")
PY

cat > "$ROOT/training/train_tier.py" <<'PY'
import json
import os
from pathlib import Path

import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from trl import SFTTrainer
from peft import LoraConfig

ROOT = Path(__file__).resolve().parents[1]
TIER = os.environ["LUMACORE_TIER"]
BASE_MODEL = os.environ["LUMACORE_BASE_MODEL"]
DATASET = Path(os.environ["LUMACORE_DATASET"])
OUTPUT = Path(os.environ["LUMACORE_OUTPUT"])
EPOCHS = float(os.environ["LUMACORE_EPOCHS"])
LR = float(os.environ["LUMACORE_LR"])
GRAD_ACCUM = int(os.environ["LUMACORE_GRAD_ACCUM"])


def choose_device():
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def main():
    if not DATASET.exists():
        raise FileNotFoundError(f"Training dataset not found: {DATASET}")

    device = choose_device()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    examples = sum(1 for _ in DATASET.open(encoding="utf-8"))

    print("\n========================================")
    print(f" LUMACORE {TIER} TRAINING")
    print("========================================")
    print(f"Base model: {BASE_MODEL}")
    print(f"Dataset:    {DATASET}")
    print(f"Examples:   {examples}")
    print(f"Output:     {OUTPUT}")
    print(f"Device:     {device}")
    print(f"Epochs:     {EPOCHS}")
    print(f"LR:         {LR}")
    print(f"Grad accum: {GRAD_ACCUM}")
    print("Method:     LoRA fine-tuning, then merge into final checkpoint")

    dataset = load_dataset("json", data_files=str(DATASET), split="train")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.float16 if device in {"cuda", "mps"} else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        trust_remote_code=True,
        torch_dtype=dtype,
        low_cpu_mem_usage=True,
    )
    model.config.use_cache = False

    lora = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "up_proj", "down_proj", "gate_proj"],
    )

    args = TrainingArguments(
        output_dir=str(OUTPUT / "checkpoints"),
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=LR,
        logging_steps=10,
        save_strategy="epoch",
        save_total_limit=2,
        report_to="none",
        remove_unused_columns=False,
        dataloader_pin_memory=False,
        gradient_checkpointing=False,
        fp16=(device == "cuda"),
        bf16=False,
    )

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
        args=args,
        peft_config=lora,
    )
    trainer.train()

    print("\nMerging LoRA adapter into the final checkpoint...")
    merged = trainer.model.merge_and_unload()
    merged.config.use_cache = True
    merged.save_pretrained(str(OUTPUT), safe_serialization=True)
    tokenizer.save_pretrained(str(OUTPUT))

    metadata = {
        "tier": TIER,
        "base_model": BASE_MODEL,
        "dataset": str(DATASET.relative_to(ROOT)),
        "examples": len(dataset),
        "epochs": EPOCHS,
        "learning_rate": LR,
        "gradient_accumulation_steps": GRAD_ACCUM,
        "method": "LoRA fine-tuning, merged into final checkpoint",
    }
    (OUTPUT / "training_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Training complete: LumaCore {TIER}")
    print(f"Merged checkpoint: {OUTPUT}")


if __name__ == "__main__":
    main()
PY

# macOS ships Bash 3.2 by default, so use case statements instead of associative arrays.
for tier in 3.2 4.0 5.7; do
  case "$tier" in
    3.2)
      base="Qwen/Qwen2.5-0.5B-Instruct"
      epochs="3"
      lr="2e-4"
      accum="8"
      count="300"
      ;;
    4.0)
      base="Qwen/Qwen2.5-1.5B-Instruct"
      epochs="4"
      lr="1.5e-4"
      accum="8"
      count="450"
      ;;
    5.7)
      base="Qwen/Qwen3-4B-Instruct-2507"
      epochs="5"
      lr="1e-4"
      accum="16"
      count="600"
      ;;
  esac

  safe_tier="${tier//./_}"
  dataset="$DATA_DIR/lumacore_${safe_tier}.jsonl"
  output="$OUTPUT_DIR/lumacore-${tier}"

  echo
  echo "----------------------------------------"
  echo "Training LumaCore $tier"
  echo "Base model: $base"
  echo "Dataset:    $dataset ($count examples)"
  echo "Output:     $output"
  echo "----------------------------------------"

  LUMACORE_TIER="$tier" \
  LUMACORE_BASE_MODEL="$base" \
  LUMACORE_DATASET="$dataset" \
  LUMACORE_OUTPUT="$output" \
  LUMACORE_EPOCHS="$epochs" \
  LUMACORE_LR="$lr" \
  LUMACORE_GRAD_ACCUM="$accum" \
  "$PYTHON" "$ROOT/training/train_tier.py"
done

if [[ -f "$ROOT/.env" ]]; then
  "$PYTHON" - <<'PY'
from pathlib import Path
import re

env = Path(".env")
text = env.read_text(encoding="utf-8")
updates = {
    "LUMACORE_3_2_CHECKPOINT": "./training/output/lumacore-3.2",
    "LUMACORE_4_0_CHECKPOINT": "./training/output/lumacore-4.0",
    "LUMACORE_5_7_CHECKPOINT": "./training/output/lumacore-5.7",
}
for key, value in updates.items():
    pattern = rf"(?m)^{re.escape(key)}=.*$"
    line = f"{key}={value}"
    if re.search(pattern, text):
        text = re.sub(pattern, line, text)
    else:
        text += ("\n" if text and not text.endswith("\n") else "") + line + "\n"
env.write_text(text, encoding="utf-8")
print(f"Updated {env} with trained checkpoint paths.")
PY
fi

echo
echo "========================================"
echo " ALL LUMACORE TIERS TRAINED"
echo "========================================"
echo "3.2 -> training/output/lumacore-3.2 (300 examples)"
echo "4.0 -> training/output/lumacore-4.0 (450 examples)"
echo "5.7 -> training/output/lumacore-5.7 (600 examples)"
echo ""
echo "The generated checkpoints are merged models and can be loaded by the normal runtime."
