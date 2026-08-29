# Lumen Architecture

Browser
    |
    v
Lumen API
    |
    v
Lumen Engine
    |
    +-- Model Registry
    |
    +-- Memory
    |
    +-- Context
    |
    +-- File handling
    |
    v
Lumen Runtime
    |
    v
Lumen Model

The runtime is deliberately separated from the API so the model
implementation can change without rewriting the frontend.
