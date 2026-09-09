from __future__ import annotations

import os
import threading
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MEDIA_DIR = ROOT / "storage" / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


class MediaGenerationError(RuntimeError):
    """Raised when a media generation request cannot be completed."""


class MediaRuntime:
    """Lazy Diffusers runtime for image and video generation."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._image_pipe: Any | None = None
        self._video_pipe: Any | None = None

    @staticmethod
    def get_device() -> str:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    @staticmethod
    def _dtype(device: str):
        import torch
        return torch.float32 if device == "cpu" else torch.float16

    def _load_image_pipeline(self):
        if self._image_pipe is not None:
            return self._image_pipe
        with self._lock:
            if self._image_pipe is not None:
                return self._image_pipe
            try:
                from diffusers import AutoPipelineForText2Image
            except ImportError as exc:
                raise MediaGenerationError("Install requirements.txt to enable image generation.") from exc
            device = self.get_device()
            checkpoint = os.getenv("LUMACORE_IMAGE_MODEL", "runwayml/stable-diffusion-v1-5").strip()
            print(f"Loading LumaCore image model on {device}: {checkpoint}")
            pipe = AutoPipelineForText2Image.from_pretrained(
                checkpoint,
                torch_dtype=self._dtype(device),
                use_safetensors=True,
            ).to(device)
            if device == "cuda":
                try:
                    pipe.enable_attention_slicing()
                except Exception:
                    pass
            self._image_pipe = pipe
            return pipe

    def _load_video_pipeline(self):
        if self._video_pipe is not None:
            return self._video_pipe
        with self._lock:
            if self._video_pipe is not None:
                return self._video_pipe
            try:
                from diffusers import CogVideoXPipeline
            except ImportError as exc:
                raise MediaGenerationError("Install requirements.txt to enable video generation.") from exc
            device = self.get_device()
            checkpoint = os.getenv("LUMACORE_VIDEO_MODEL", "THUDM/CogVideoX-2b").strip()
            print(f"Loading LumaCore video model on {device}: {checkpoint}")
            pipe = CogVideoXPipeline.from_pretrained(
                checkpoint,
                torch_dtype=self._dtype(device),
            ).to(device)
            try:
                pipe.enable_attention_slicing()
            except Exception:
                pass
            try:
                pipe.vae.enable_slicing()
            except Exception:
                pass
            try:
                pipe.vae.enable_tiling()
            except Exception:
                pass
            self._video_pipe = pipe
            return pipe

    def generate_image(self, prompt: str, width: int = 512, height: int = 512, steps: int = 20, seed: int | None = None) -> Path:
        prompt = prompt.strip()
        if not prompt:
            raise MediaGenerationError("Image prompt cannot be empty.")
        width = max(256, min(width, 1024))
        height = max(256, min(height, 1024))
        steps = max(1, min(steps, 60))
        pipe = self._load_image_pipeline()
        generator = None
        if seed is not None:
            import torch
            generator = torch.Generator(device=self.get_device()).manual_seed(seed)
        try:
            image = pipe(prompt=prompt, width=width, height=height, num_inference_steps=steps, generator=generator).images[0]
        except Exception as exc:
            raise MediaGenerationError(f"Image generation failed: {exc}") from exc
        path = MEDIA_DIR / f"image-{uuid.uuid4().hex}.png"
        image.save(path, format="PNG")
        return path

    def generate_video(self, prompt: str, steps: int = 20, seed: int | None = None, fps: int = 8) -> Path:
        prompt = prompt.strip()
        if not prompt:
            raise MediaGenerationError("Video prompt cannot be empty.")
        steps = max(1, min(steps, 50))
        fps = max(1, min(fps, 30))
        pipe = self._load_video_pipeline()
        generator = None
        if seed is not None:
            import torch
            generator = torch.Generator(device=self.get_device()).manual_seed(seed)
        try:
            output = pipe(prompt=prompt, guidance_scale=6, num_inference_steps=steps, generator=generator)
            frames = output.frames[0]
            from diffusers.utils import export_to_video
            path = MEDIA_DIR / f"video-{uuid.uuid4().hex}.mp4"
            export_to_video(frames, str(path), fps=fps)
            return path
        except Exception as exc:
            raise MediaGenerationError(f"Video generation failed: {exc}") from exc


media_runtime = MediaRuntime()
