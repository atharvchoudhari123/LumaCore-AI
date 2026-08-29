# Lumen Training

The first Lumen training prototype uses supervised fine-tuning.

## Dataset

training/data/lumen_train.jsonl

Each example uses a conversation format:

{
  "messages": [
    {
      "role": "user",
      "content": "Question"
    },
    {
      "role": "assistant",
      "content": "Answer"
    }
  ]
}

## Train

Activate your virtual environment and run:

python3 training/train_sft.py

The default output is:

training/output/lumen-3.2

## Scaling

The included dataset is only a development example.

A strong Lumen model requires much larger and higher-quality
datasets, evaluation, post-training and substantially more compute.
