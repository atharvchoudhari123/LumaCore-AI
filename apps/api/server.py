import json
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv

import sys
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2])
)

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException
)

from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    StreamingResponse
)

from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parents[2]

load_dotenv(
    ROOT / ".env"
)

UPLOADS = (
    ROOT /
    "storage" /
    "uploads"
)

UPLOADS.mkdir(
    parents=True,
    exist_ok=True
)

from engine.engine import engine
from engine.model_registry import (
    get_models,
    get_model
)


app = FastAPI(
    title="Lumen API",
    version="0.1.0"
)


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):

    model: str = "lumen-4.0"

    messages: list[Message] = Field(
        default_factory=list
    )

    mode: str = "chat"

    stream: bool = False

    max_new_tokens: int = 512


@app.get("/health")
async def health():

    return {
        "ok": True,
        "service": "lumen-api",
        "version": "0.1.0"
    }


@app.get("/v1/models")
async def models():

    return {
        "object": "list",

        "data": [
            {
                "id": model["id"],
                "object": "model",
                "owned_by": "lumen"
            }

            for model in get_models()
        ]
    }


@app.post("/v1/files")
async def upload_files(
    files: list[UploadFile] = File(...)
):

    results = []

    maximum_size = (
        int(
            os.getenv(
                "LUMEN_MAX_FILE_MB",
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
        ".h"
    }

    for upload in files:

        content = await upload.read()

        if len(content) > maximum_size:

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
            content
        )

        text = None

        extension = Path(
            upload.filename or ""
        ).suffix.lower()

        if extension in text_extensions:

            try:

                text = content.decode(
                    "utf-8"
                )

            except UnicodeDecodeError:

                text = None

        results.append({

            "id": file_id,

            "name":
                upload.filename,

            "size":
                len(content),

            "content_type":
                upload.content_type,

            "text":
                text

        })

    return {
        "data": results
    }


@app.get("/v1/files/{file_id}")
async def get_file(file_id: str):

    target = (
        UPLOADS /
        file_id
    )

    if not target.exists():

        raise HTTPException(
            status_code=404,
            detail="File not found."
        )

    return FileResponse(
        target
    )


@app.post("/v1/chat/completions")
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
        for message in request.messages
    ]

    try:

        text = engine.complete(

            model_id=request.model,

            messages=messages,

            mode=request.mode,

            max_new_tokens=
                request.max_new_tokens

        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    if not request.stream:

        return {

            "id":
                f"lumen-{uuid.uuid4().hex}",

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
                    f"lumen-{uuid.uuid4().hex}",

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

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type=
            "text/event-stream"
    )


@app.get("/")
async def index():

    page = (
        ROOT /
        "apps" /
        "web" /
        "index.html"
    )

    return HTMLResponse(
        page.read_text(
            encoding="utf-8"
        )
    )


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        "apps.api.server:app",

        host=os.getenv(
            "LUMEN_HOST",
            "0.0.0.0"
        ),

        port=int(
            os.getenv(
                "LUMEN_PORT",
                "3000"
            )
        ),

        reload=False

    )
