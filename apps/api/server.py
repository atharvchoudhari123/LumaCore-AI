from __future__ import annotations

import json
import os
import sys
import uuid

from pathlib import Path

ROOT = Path(
    __file__
).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT)
)

from dotenv import load_dotenv

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    UploadFile
)

from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    StreamingResponse
)

from pydantic import (
    BaseModel,
    Field
)

from engine.model_registry import (
    get_model,
    get_models
)

from plugins.registry import (
    PluginError,
    get_plugin,
    list_plugins,
    run_plugin
)


load_dotenv(
    ROOT / ".env"
)


UPLOADS = (
    ROOT
    / "storage"
    / "uploads"
)

UPLOADS.mkdir(
    parents=True,
    exist_ok=True
)


app = FastAPI(
    title="LumaCore API",
    version="0.4.0"
)


FAST_MODE = (
    os.getenv(
        "LUMACORE_FAST_MODE",
        "false"
    )
    .strip()
    .lower()
    == "true"
)


# =========================================================
# DATA MODELS
# =========================================================

class Message(BaseModel):
    role: str
    content: str


class ChatFile(BaseModel):
    name: str
    type: str | None = None
    size: int | None = None
    text: str | None = None


class ChatRequest(BaseModel):

    model: str = (
        "lumacore-4.0"
    )

    messages: list[Message] = Field(
        default_factory=list
    )

    files: list[ChatFile] = Field(
        default_factory=list
    )

    mode: str = "chat"

    stream: bool = False

    max_new_tokens: int = 768

    plugins: list[str] = Field(
        default_factory=list
    )


# =========================================================
# HEALTH
# =========================================================

@app.get(
    "/health"
)
async def health():

    return {
        "ok": True,
        "service": "lumacore-api",
        "version": "0.4.0",
        "fast_mode": FAST_MODE
    }


# =========================================================
# MODELS
# =========================================================

@app.get(
    "/v1/models"
)
async def models():

    return {
        "object": "list",
        "data": [
            {
                "id": model["id"],
                "object": "model",
                "owned_by": "lumacore",
                "display_name": model[
                    "display_name"
                ],
                "capabilities": model.get(
                    "capabilities",
                    []
                )
            }
            for model in get_models()
        ]
    }


# =========================================================
# PLUGINS
# =========================================================

@app.get(
    "/v1/plugins"
)
async def plugins():

    return {
        "object": "list",
        "data": list_plugins()
    }


@app.post(
    "/v1/plugins/{plugin_id}/run"
)
async def plugin_run(
    plugin_id: str,
    arguments: dict | None = None
):

    if get_plugin(
        plugin_id
    ) is None:

        raise HTTPException(
            status_code=404,
            detail="Plugin not found."
        )

    try:

        return run_plugin(
            plugin_id,
            arguments or {}
        )

    except PluginError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        ) from error


# =========================================================
# FILE UPLOADS
# =========================================================

@app.post(
    "/v1/files"
)
async def upload_files(
    files: list[UploadFile] = File(...)
):

    max_size = (
        int(
            os.getenv(
                "LUMACORE_MAX_FILE_MB",
                "50"
            )
        )
        * 1024
        * 1024
    )


    text_extensions = {
        ".txt",
        ".md",
        ".json",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".py",
        ".html",
        ".css",
        ".csv",
        ".xml",
        ".yaml",
        ".yml",
        ".sql",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".sh",
        ".swift"
    }


    results = []


    for upload in files:

        data = await upload.read()


        if len(data) > max_size:

            raise HTTPException(
                status_code=413,
                detail="File is too large."
            )


        file_id = uuid.uuid4().hex


        destination = (
            UPLOADS /
            file_id
        )


        destination.write_bytes(
            data
        )


        text = None


        suffix = Path(
            upload.filename or ""
        ).suffix.lower()


        if suffix in text_extensions:

            try:

                text = data.decode(
                    "utf-8"
                )

            except UnicodeDecodeError:

                text = None


        results.append(
            {
                "id": file_id,
                "name": upload.filename,
                "size": len(data),
                "content_type": upload.content_type,
                "text": text
            }
        )


    return {
        "data": results
    }


@app.get(
    "/v1/files/{file_id}"
)
async def get_file(
    file_id: str
):

    target = (
        UPLOADS /
        file_id
    )


    if (
        not target.exists()
        or
        not target.is_file()
    ):

        raise HTTPException(
            status_code=404,
            detail="File not found."
        )


    return FileResponse(
        target
    )


# =========================================================
# SECURITY REVIEW
# =========================================================

@app.post(
    "/v1/security/review"
)
async def security_review(
    payload: dict
):

    files = payload.get(
        "files",
        []
    )


    if not isinstance(
        files,
        list
    ):

        raise HTTPException(
            status_code=400,
            detail="files must be a list."
        )


    try:

        from engine.engine import engine

        return engine.security_review(
            files
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        ) from error


# =========================================================
# FAST DEVELOPMENT RESPONSE
# =========================================================

def make_fast_response(
    request: ChatRequest
) -> str:

    if not request.messages:

        return (
            "Hello! How can I help you?"
        )


    user_text = (
        request.messages[-1]
        .content
        .strip()
    )


    if not user_text:

        return (
            "Hello! How can I help you?"
        )


    lower = user_text.lower()


    # ---------------------------------------------
    # BASIC GREETINGS
    # ---------------------------------------------

    if lower in {
        "hi",
        "hello",
        "hey",
        "yo",
        "hiya"
    }:

        return (
            "Hello! How can I help you today?"
        )


    # ---------------------------------------------
    # IDENTITY
    # ---------------------------------------------

    if lower in {
        "who are you",
        "what are you",
        "what is lumacore"
    }:

        return (
            "I'm LumaCore, an AI assistant."
        )


    # ---------------------------------------------
    # CODING
    # ---------------------------------------------

    if request.mode == "code":

        return (
            "Coding mode is ready. "
            "Describe the project or code you want to build."
        )


    # ---------------------------------------------
    # SECURITY
    # ---------------------------------------------

    if request.mode == "security":

        return (
            "Security review mode is ready. "
            "Provide the application code or files you want reviewed."
        )


    # ---------------------------------------------
    # SIMPLE CALCULATOR
    # ---------------------------------------------

    if (
        lower.startswith("calculate ")
        or
        lower.startswith("compute ")
    ):

        expression = user_text.split(
            " ",
            1
        )[1].strip()


        try:

            result = run_plugin(
                "calculator",
                {
                    "expression":
                        expression
                }
            )


            return (
                str(
                    result[
                        "result"
                    ]
                )
            )

        except Exception:

            pass


    # ---------------------------------------------
    # GENERIC CHAT
    # ---------------------------------------------

    return (
        "I'm ready to help."
    )


# =========================================================
# CHAT COMPLETIONS
# =========================================================

@app.post(
    "/v1/chat/completions"
)
async def chat(
    request: ChatRequest
):

    if not request.messages:

        raise HTTPException(
            status_code=400,
            detail="messages is required."
        )


    if get_model(
        request.model
    ) is None:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown model: "
                f"{request.model}"
            )
        )


    messages = [
        message.model_dump()
        for message
        in request.messages
    ]


    files = [
        file.model_dump()
        for file
        in request.files
    ]


    # =====================================================
    # FAST MODE
    # =====================================================

    if FAST_MODE:

        text = make_fast_response(
            request
        )


    # =====================================================
    # REAL MODEL
    # =====================================================

    else:

        try:

            from engine.engine import engine


            text = engine.complete(

                model_id=
                    request.model,

                messages=
                    messages,

                files=
                    files,

                mode=
                    request.mode,

                max_new_tokens=
                    request.max_new_tokens,

                plugins=
                    request.plugins

            )


        except Exception as error:

            raise HTTPException(
                status_code=500,
                detail=str(error)
            ) from error


    response_id = (
        f"lumacore-{uuid.uuid4().hex}"
    )


    # =====================================================
    # NORMAL RESPONSE
    # =====================================================

    if not request.stream:

        return {

            "id":
                response_id,

            "object":
                "chat.completion",

            "model":
                request.model,

            "choices": [

                {

                    "index":
                        0,

                    "message": {

                        "role":
                            "assistant",

                        "content":
                            text

                    },

                    "finish_reason":
                        "stop"

                }

            ]

        }


    # =====================================================
    # STREAMING RESPONSE
    # =====================================================

    def event_stream():

        for index in range(
            0,
            len(text),
            80
        ):

            chunk = text[
                index:index + 80
            ]


            payload = {

                "id":
                    response_id,

                "object":
                    "chat.completion.chunk",

                "model":
                    request.model,

                "choices": [

                    {

                        "index":
                            0,

                        "delta": {

                            "content":
                                chunk

                        },

                        "finish_reason":
                            None

                    }

                ]

            }


            yield (
                "data: "
                +
                json.dumps(
                    payload
                )
                +
                "\n\n"
            )


        yield (
            "data: [DONE]\n\n"
        )


    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )


# =========================================================
# FRONTEND
# =========================================================

@app.get(
    "/"
)
async def index():

    page = (
        ROOT
        / "apps"
        / "web"
        / "index.html"
    )


    if not page.exists():

        raise HTTPException(
            status_code=404,
            detail="LumaCore web app not found."
        )


    return HTMLResponse(
        page.read_text(
            encoding="utf-8"
        )
    )


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    import uvicorn


    uvicorn.run(

        "apps.api.server:app",

        host=os.getenv(
            "LUMACORE_HOST",
            "0.0.0.0"
        ),

        port=int(
            os.getenv(
                "LUMACORE_PORT",
                "3000"
            )
        ),

        reload=False

    )