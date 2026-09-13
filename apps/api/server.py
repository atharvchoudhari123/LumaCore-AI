from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from engine.context import attach_files, build_system_prompt
from engine.model_registry import get_model, get_models
from plugins.registry import PluginError, get_plugin, list_plugins, run_plugin

load_dotenv(ROOT / ".env")

UPLOADS = ROOT / "storage" / "uploads"
MEDIA = ROOT / "storage" / "media"
UPLOADS.mkdir(parents=True, exist_ok=True)
MEDIA.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="LumaCore API", version="0.5.0")

FAST_MODE = os.getenv("LUMACORE_FAST_MODE", "false").strip().lower() == "true"


class Message(BaseModel):
    role: str
    content: str


class ChatFile(BaseModel):
    name: str
    type: str | None = None
    size: int | None = None
    text: str | None = None


class ChatRequest(BaseModel):
    model: str = "lumacore-4.0"
    messages: list[Message] = Field(default_factory=list)
    files: list[ChatFile] = Field(default_factory=list)
    mode: str = "chat"
    stream: bool = False
    max_new_tokens: int = 768
    plugins: list[str] = Field(default_factory=list)


class MediaRequest(BaseModel):
    prompt: str
    width: int = 512
    height: int = 512
    steps: int = 20
    seed: int | None = None
    fps: int = 8


def media_url(path: Path) -> str:
    return f"/v1/media/files/{path.name}"


def uses_fable_5_1(model_id: str) -> bool:
    return (
        model_id == "lumacore-5.7"
        and os.getenv("LUMACORE_5_7_PROVIDER", "local").strip().lower() == "anthropic"
    )


@app.get("/health")
async def health():
    return {
        "ok": True,
        "service": "lumacore-api",
        "version": "0.5.0",
        "fast_mode": FAST_MODE,
        "fable_5_1": {
            "enabled": uses_fable_5_1("lumacore-5.7"),
            "model": os.getenv("LUMACORE_5_7_ANTHROPIC_MODEL", "claude-fable-5-1"),
        },
        "media": {"image": True, "video": True},
    }


@app.get("/v1/models")
async def models():
    return {
        "object": "list",
        "data": [
            {
                "id": model["id"],
                "object": "model",
                "owned_by": "lumacore",
                "display_name": model["display_name"],
                "capabilities": model.get("capabilities", []),
            }
            for model in get_models()
        ],
    }


@app.get("/v1/plugins")
async def plugins():
    return {"object": "list", "data": list_plugins()}


@app.post("/v1/plugins/{plugin_id}/run")
async def plugin_run(plugin_id: str, arguments: dict | None = None):
    if get_plugin(plugin_id) is None:
        raise HTTPException(status_code=404, detail="Plugin not found.")
    try:
        return run_plugin(plugin_id, arguments or {})
    except PluginError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/v1/files")
async def upload_files(files: list[UploadFile] = File(...)):
    max_size = int(os.getenv("LUMACORE_MAX_FILE_MB", "50")) * 1024 * 1024
    text_extensions = {
        ".txt", ".md", ".json", ".js", ".ts", ".tsx", ".jsx", ".py",
        ".html", ".css", ".csv", ".xml", ".yaml", ".yml", ".sql",
        ".java", ".c", ".cpp", ".h", ".sh", ".swift",
    }
    results = []
    for upload in files:
        data = await upload.read()
        if len(data) > max_size:
            raise HTTPException(status_code=413, detail="File is too large.")
        file_id = uuid.uuid4().hex
        destination = UPLOADS / file_id
        destination.write_bytes(data)
        text = None
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix in text_extensions:
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                pass
        results.append({
            "id": file_id,
            "name": upload.filename,
            "size": len(data),
            "content_type": upload.content_type,
            "text": text,
        })
    return {"data": results}


@app.get("/v1/files/{file_id}")
async def get_file(file_id: str):
    target = UPLOADS / file_id
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(target)


@app.get("/media.js")
async def media_js():
    page = ROOT / "apps" / "web" / "media.js"
    if not page.exists():
        raise HTTPException(status_code=404, detail="Media UI not found.")
    return FileResponse(page, media_type="application/javascript")


@app.get("/v1/media")
async def media_capabilities():
    return {
        "image_generation": {
            "enabled": True,
            "model": os.getenv("LUMACORE_IMAGE_MODEL", "stable-diffusion-v1-5/stable-diffusion-v1-5"),
        },
        "video_generation": {
            "enabled": True,
            "model": os.getenv("LUMACORE_VIDEO_MODEL", "zai-org/CogVideoX-2b"),
        },
    }


@app.post("/v1/media/images")
async def generate_image(request: MediaRequest):
    try:
        from engine.media import media_runtime
        path = media_runtime.generate_image(
            request.prompt,
            width=request.width,
            height=request.height,
            steps=request.steps,
            seed=request.seed,
        )
        return {
            "type": "image",
            "filename": path.name,
            "url": media_url(path),
            "prompt": request.prompt,
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.post("/v1/media/videos")
async def generate_video(request: MediaRequest):
    try:
        from engine.media import media_runtime
        path = media_runtime.generate_video(
            request.prompt,
            steps=request.steps,
            seed=request.seed,
            fps=request.fps,
        )
        return {
            "type": "video",
            "filename": path.name,
            "url": media_url(path),
            "prompt": request.prompt,
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/v1/media/files/{filename}")
async def get_media_file(filename: str):
    # Resolve inside MEDIA and prevent path traversal.
    target = (MEDIA / Path(filename).name).resolve()
    if target.parent != MEDIA.resolve() or not target.is_file():
        raise HTTPException(status_code=404, detail="Media file not found.")
    return FileResponse(target)


@app.post("/v1/security/review")
async def security_review(payload: dict):
    files = payload.get("files", [])
    if not isinstance(files, list):
        raise HTTPException(status_code=400, detail="files must be a list.")
    try:
        from engine.engine import engine
        return engine.security_review(files)
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


def make_fast_response(request: ChatRequest) -> str:
    if not request.messages:
        return "Hello! How can I help you?"
    user_text = request.messages[-1].content.strip()
    if not user_text:
        return "Hello! How can I help you?"
    lower = user_text.lower()
    if lower in {"hi", "hello", "hey", "yo", "hiya"}:
        return "Hello! How can I help you today?"
    if lower in {"who are you", "what are you", "what is lumacore"}:
        return "I'm LumaCore, an AI assistant."
    if request.mode == "code":
        return "Coding mode is ready. Describe the project or code you want to build."
    if request.mode == "security":
        return "Security review mode is ready. Provide the application code or files you want reviewed."
    if lower.startswith("calculate ") or lower.startswith("compute "):
        expression = user_text.split(" ", 1)[1].strip()
        try:
            result = run_plugin("calculator", {"expression": expression})
            return str(result["result"])
        except Exception:
            pass
    return "I'm ready to help."


def media_intent(text: str) -> str | None:
    value = text.lower().strip()
    video_terms = ("generate a video", "generate video", "make a video", "create a video", "generate me a video")
    image_terms = ("generate an image", "generate image", "make an image", "create an image", "generate me an image", "draw me")
    if any(term in value for term in video_terms):
        return "video"
    if any(term in value for term in image_terms):
        return "image"
    return None


@app.post("/v1/chat/completions")
async def chat(request: ChatRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages is required.")
    if get_model(request.model) is None:
        raise HTTPException(status_code=400, detail=f"Unknown model: {request.model}")

    messages = [message.model_dump() for message in request.messages]
    files = [file.model_dump() for file in request.files]
    media_kind = media_intent(request.messages[-1].content)

    # Dedicated media generation preserves normal chat/coding/security flows.
    if media_kind:
        prompt = request.messages[-1].content
        try:
            from engine.media import media_runtime
            if media_kind == "image":
                path = media_runtime.generate_image(prompt)
            else:
                path = media_runtime.generate_video(prompt)
            text = f"Generated your {media_kind}."
            media = {
                "type": media_kind,
                "filename": path.name,
                "url": media_url(path),
                "prompt": prompt,
            }
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error)) from error
    elif uses_fable_5_1(request.model):
        # LumaCore 5.7 keeps its public model identity while using Claude
        # Fable 5.1 for hosted inference. The same system prompt and uploaded
        # text-file context used by the local engine are preserved here.
        try:
            from engine.anthropic_runtime import anthropic_runtime
            normalized = attach_files(messages, files)
            system = build_system_prompt("LumaCore 5.7", request.mode)
            final_messages = [
                {"role": "system", "content": system},
                *normalized,
            ]
            text = anthropic_runtime.generate(
                model=os.getenv("LUMACORE_5_7_ANTHROPIC_MODEL", "claude-fable-5-1"),
                messages=final_messages,
                max_new_tokens=request.max_new_tokens,
            )
            media = None
        except Exception as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
    else:
        media = None
        if FAST_MODE:
            text = make_fast_response(request)
        else:
            try:
                from engine.engine import engine
                text = engine.complete(
                    model_id=request.model,
                    messages=messages,
                    files=files,
                    mode=request.mode,
                    max_new_tokens=request.max_new_tokens,
                    plugins=request.plugins,
                )
            except Exception as error:
                raise HTTPException(status_code=500, detail=str(error)) from error

    response_id = f"lumacore-{uuid.uuid4().hex}"
    if not request.stream:
        response = {
            "id": response_id,
            "object": "chat.completion",
            "model": request.model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }],
        }
        if media:
            response["media"] = media
        return response

    def event_stream():
        for index in range(0, len(text), 80):
            chunk = text[index:index + 80]
            payload = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "delta": {"content": chunk},
                    "finish_reason": None,
                }],
            }
            yield "data: " + json.dumps(payload) + "\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/")
async def index():
    page = ROOT / "apps" / "web" / "index.html"
    if not page.exists():
        raise HTTPException(status_code=404, detail="LumaCore web app not found.")
    html = page.read_text(encoding="utf-8")
    if "/media.js" not in html:
        html = html.replace("</body>", '<script src="/media.js"></script>\n</body>')
    return HTMLResponse(html)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "apps.api.server:app",
        host=os.getenv("LUMACORE_HOST", "0.0.0.0"),
        port=int(os.getenv("LUMACORE_PORT", "3000")),
        reload=False,
    )
