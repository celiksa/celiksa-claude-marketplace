"""HTTP and WebSocket client for ComfyUI's REST API."""

import asyncio
import json
import os
import random
import time
import uuid
from pathlib import Path

import httpx
import websockets


class ComfyUIClient:
    """Async client for ComfyUI's HTTP and WebSocket APIs."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8188):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.ws_url = f"ws://{host}:{port}/ws"
        self.client_id = str(uuid.uuid4())
        self._object_info_cache: dict | None = None

    async def is_running(self) -> bool:
        """Check if ComfyUI is reachable."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/system_stats")
                return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def get_system_stats(self) -> dict:
        """GET /system_stats - returns GPU/CPU/memory info."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/system_stats")
            resp.raise_for_status()
            return resp.json()

    async def get_queue_info(self) -> dict:
        """GET /queue - returns running and pending queue items."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/queue")
            resp.raise_for_status()
            return resp.json()

    async def get_models(self, folder: str) -> list[str]:
        """GET /models/{folder} - list model files in a category."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/models/{folder}")
            resp.raise_for_status()
            return resp.json()

    async def get_all_models(self) -> dict[str, list[str]]:
        """Get models for all common categories."""
        categories = [
            "checkpoints", "diffusion_models", "text_encoders", "clip",
            "vae", "loras", "controlnet", "upscale_models", "embeddings",
        ]
        result = {}
        async with httpx.AsyncClient(timeout=10.0) as client:
            for cat in categories:
                try:
                    resp = await client.get(f"{self.base_url}/models/{cat}")
                    if resp.status_code == 200:
                        models = resp.json()
                        if models:
                            result[cat] = models
                except Exception:
                    continue
        return result

    async def get_object_info(self, filter_str: str = "") -> dict:
        """GET /object_info - all registered node types (cached)."""
        if self._object_info_cache is None:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{self.base_url}/object_info")
                resp.raise_for_status()
                self._object_info_cache = resp.json()

        if not filter_str:
            return self._object_info_cache

        filter_lower = filter_str.lower()
        return {
            k: v for k, v in self._object_info_cache.items()
            if filter_lower in k.lower()
            or filter_lower in (v.get("display_name") or "").lower()
            or filter_lower in (v.get("category") or "").lower()
        }

    async def get_history(self, prompt_id: str) -> dict:
        """GET /history/{prompt_id} - execution results."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/history/{prompt_id}")
            resp.raise_for_status()
            return resp.json()

    async def upload_image(self, filepath: str, subfolder: str = "") -> dict:
        """POST /upload/image - upload an image file."""
        path = Path(filepath)
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(path, "rb") as f:
                files = {"image": (path.name, f, "image/png")}
                data = {}
                if subfolder:
                    data["subfolder"] = subfolder
                resp = await client.post(
                    f"{self.base_url}/upload/image",
                    files=files,
                    data=data,
                )
                resp.raise_for_status()
                return resp.json()

    async def queue_prompt(self, workflow: dict, prompt_id: str | None = None) -> dict:
        """POST /prompt - queue a workflow for execution."""
        if prompt_id is None:
            prompt_id = str(uuid.uuid4())
        payload = {
            "prompt": workflow,
            "client_id": self.client_id,
            "prompt_id": prompt_id,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self.base_url}/prompt",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def queue_and_wait(
        self, workflow: dict, timeout: float = 600.0
    ) -> dict:
        """
        Full generation cycle:
        1. Connect WebSocket
        2. POST /prompt
        3. Wait for execution completion via WebSocket
        4. GET /history to retrieve results
        5. Return structured result with output images

        Falls back to polling if WebSocket fails.
        """
        prompt_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            result = await self._queue_and_wait_ws(workflow, prompt_id, timeout)
        except Exception:
            # Fallback to polling
            result = await self._queue_and_wait_poll(workflow, prompt_id, timeout)

        elapsed = time.time() - start_time
        result["elapsed_seconds"] = round(elapsed, 2)
        return result

    async def _queue_and_wait_ws(
        self, workflow: dict, prompt_id: str, timeout: float
    ) -> dict:
        """WebSocket-based wait for completion."""
        ws_uri = f"{self.ws_url}?clientId={self.client_id}"

        async with websockets.connect(ws_uri) as ws:
            # Queue the prompt
            await self.queue_prompt(workflow, prompt_id)

            # Listen for completion
            deadline = time.time() + timeout
            while time.time() < deadline:
                try:
                    raw = await asyncio.wait_for(
                        ws.recv(), timeout=min(30.0, deadline - time.time())
                    )
                except asyncio.TimeoutError:
                    continue

                if isinstance(raw, str):
                    message = json.loads(raw)
                    msg_type = message.get("type")
                    data = message.get("data", {})

                    if msg_type == "executing":
                        if (
                            data.get("node") is None
                            and data.get("prompt_id") == prompt_id
                        ):
                            # Execution complete
                            break
                    elif msg_type == "execution_error":
                        if data.get("prompt_id") == prompt_id:
                            return {
                                "prompt_id": prompt_id,
                                "status": "error",
                                "error": data.get("exception_message", "Unknown error"),
                                "images": [],
                            }
                # Binary frames are preview images - skip them
            else:
                return {
                    "prompt_id": prompt_id,
                    "status": "timeout",
                    "error": f"Generation timed out after {timeout}s",
                    "images": [],
                }

        return await self._collect_results(prompt_id)

    async def _queue_and_wait_poll(
        self, workflow: dict, prompt_id: str, timeout: float
    ) -> dict:
        """Polling-based fallback for when WebSocket fails."""
        await self.queue_prompt(workflow, prompt_id)

        deadline = time.time() + timeout
        while time.time() < deadline:
            await asyncio.sleep(2.0)
            try:
                history = await self.get_history(prompt_id)
                if prompt_id in history:
                    entry = history[prompt_id]
                    status = entry.get("status", {})
                    if status.get("completed", False) or "outputs" in entry:
                        return await self._collect_results(prompt_id)
                    if status.get("status_str") == "error":
                        return {
                            "prompt_id": prompt_id,
                            "status": "error",
                            "error": str(status.get("messages", "Unknown error")),
                            "images": [],
                        }
            except Exception:
                continue

        return {
            "prompt_id": prompt_id,
            "status": "timeout",
            "error": f"Generation timed out after {timeout}s",
            "images": [],
        }

    async def _collect_results(self, prompt_id: str) -> dict:
        """Fetch history and extract output images."""
        history = await self.get_history(prompt_id)

        if prompt_id not in history:
            return {
                "prompt_id": prompt_id,
                "status": "error",
                "error": "Prompt not found in history",
                "images": [],
            }

        entry = history[prompt_id]
        outputs = entry.get("outputs", {})
        images = []

        comfyui_root = os.environ.get("COMFYUI_ROOT", "")
        output_dir = os.path.join(comfyui_root, "ComfyUI", "output")

        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for img in node_output["images"]:
                    filename = img["filename"]
                    subfolder = img.get("subfolder", "")
                    folder_type = img.get("type", "output")

                    if subfolder:
                        local_path = os.path.join(output_dir, subfolder, filename)
                    else:
                        local_path = os.path.join(output_dir, filename)

                    view_url = (
                        f"{self.base_url}/view?"
                        f"filename={filename}"
                        f"&subfolder={subfolder}"
                        f"&type={folder_type}"
                    )

                    images.append({
                        "filename": filename,
                        "subfolder": subfolder,
                        "type": folder_type,
                        "path": local_path.replace("\\", "/"),
                        "url": view_url,
                    })

        return {
            "prompt_id": prompt_id,
            "status": "completed",
            "images": images,
        }

    async def interrupt(self) -> None:
        """POST /interrupt - stop current generation."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{self.base_url}/interrupt")

    def get_view_url(
        self, filename: str, subfolder: str = "", folder_type: str = "output"
    ) -> str:
        """Construct a /view URL for an image."""
        return (
            f"{self.base_url}/view?"
            f"filename={filename}&subfolder={subfolder}&type={folder_type}"
        )
