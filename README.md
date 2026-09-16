# LumaCore

LumaCore is a self-hosted AI platform.

It contains:

- LumaCore API
- LumaCore Engine
- Model registry
- Model runtime
- Training pipeline
- File handling
- Web interface
- Coding Playground
- Docker configuration

## LumaCore models

LumaCore 3.2
LumaCore 4.0
LumaCore 5.7

These are the LumaCore product tiers.

The actual model checkpoints are configured separately.

## Architecture

Browser
    |
    v
LumaCore API
    |
    v
LumaCore Engine
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
LumaCore Runtime
    |
    v
LumaCore Model

## Install

Create a virtual environment:

    python3 -m venv .venv

Activate it:

    source .venv/bin/activate

Install dependencies:

    pip install -r requirements.txt

## Train all LumaCore model tiers

Run the single training script to build the separate 3.2, 4.0, and 5.7 checkpoints:

    chmod +x train_all.sh
    ./train_all.sh

The script creates the tier-specific training data/configuration it needs, trains each tier separately, saves the checkpoints under `training/output/`, and updates the local `.env` checkpoint paths.

The resulting model directories are:

    training/output/lumacore-3.2
    training/output/lumacore-4.0
    training/output/lumacore-5.7

## Configure environment

Copy the example environment file:

    cp .env.example .env

If you have already trained the models, make sure `.env` points each tier to its corresponding checkpoint directory.

## Start

    python3 apps/api/server.py

Open:

    http://localhost:3000

## Important

This repository contains the LumaCore software platform and training infrastructure.

The quality of each model depends on the base checkpoint, training data, training configuration, and available compute. The training script creates separate checkpoints for 3.2, 4.0, and 5.7; it does not by itself guarantee frontier-scale capabilities.
