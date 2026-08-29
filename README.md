# Lumen

Lumen is a self-hosted AI platform.

It contains:

- Lumen API
- Lumen Engine
- Model registry
- Model runtime
- Training pipeline
- File handling
- Web interface
- Coding Playground
- Docker configuration

## Lumen models

Lumen 3.2
Lumen 4.0
Lumen 5.7

These are the Lumen product tiers.

The actual model checkpoints are configured separately.

## Architecture

Browser
    |
    v
Lumen API
    |
    v
Lumen Engine
    |
    +-- Memory
    |
    +-- Context
    |
    +-- Files
    |
    +-- Model Router
    |
    v
Lumen Runtime
    |
    v
Lumen Model

## Install

Create a virtual environment:

    python3 -m venv .venv

Activate it:

    source .venv/bin/activate

Install dependencies:

    pip install -r requirements.txt

Copy the environment file:

    cp .env.example .env

## Start

    python3 apps/api/server.py

Open:

    http://localhost:3000

## Training

The first training prototype is located in:

    training/train_sft.py

The sample dataset is:

    training/data/lumen_train.jsonl

## Important

This repository contains the Lumen software platform and
training infrastructure.

It does not automatically contain a frontier-scale trained
model. A real checkpoint must be trained or supplied and then
configured through the Lumen runtime.
