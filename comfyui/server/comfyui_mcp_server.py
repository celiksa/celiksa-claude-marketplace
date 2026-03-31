"""
ComfyUI MCP Server - Wraps ComfyUI's REST API as Claude Code tools.

Run with: uv run comfyui_mcp_server.py
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "mcp[cli]>=1.0",
#     "httpx>=0.27",
#     "websockets>=12.0",
# ]
# ///

import json
import os
import random
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from comfyui_client import ComfyUIClient
from workflow_templates import TemplateManager

# Configuration
COMFYUI_ROOT = os.environ.get("COMFYUI_ROOT", "")
COMFYUI_HOST = os.environ.get("COMFYUI_HOST", "127.0.0.1")
COMFYUI_PORT = int(os.environ.get("COMFYUI_PORT", "8188"))

if not COMFYUI_ROOT:
    # Auto-detect common locations
    candidates = [
        os.path.expanduser("~/ComfyUI"),
        os.path.expanduser("~/AI/ComfyUI"),
        "/opt/ComfyUI",
    ]
    # Windows: check all drive letters
    if sys.platform == "win32":
        for drive in "CDEFG":
            candidates.append(f"{drive}:/ComfyUI")
            candidates.append(f"{drive}:/AI/ComfyUI")
            candidates.append(f"{drive}:/StabilityMatrix/Packages/ComfyUI")
    # Linux/Mac extras
    else:
        candidates.append(os.path.expanduser("~/.local/share/ComfyUI"))

    for candidate in candidates:
        if os.path.isdir(os.path.join(candidate, "ComfyUI")):
            COMFYUI_ROOT = candidate
            break

# Initialize
server = Server("comfyui")
client = ComfyUIClient(host=COMFYUI_HOST, port=COMFYUI_PORT)
templates = TemplateManager(
    str(Path(__file__).parent.parent / "templates")
)


def _text(content: str) -> list[TextContent]:
    """Helper to wrap a string as MCP TextContent."""
    return [TextContent(type="text", text=content)]


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Register all available tools."""
    return [
        Tool(
            name="comfyui_status",
            description=(
                "Check if ComfyUI is running and return system stats "
                "(GPU, VRAM, queue status). Call this first before any generation."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="comfyui_start",
            description=(
                "Start ComfyUI if it's not running. Launches the ComfyUI process "
                "and waits for it to become ready."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "wait_seconds": {
                        "type": "integer",
                        "description": "Max seconds to wait for startup (default: 60)",
                        "default": 60,
                    },
                },
            },
        ),
        Tool(
            name="comfyui_models",
            description=(
                "List installed models by category. Categories: diffusion_models, "
                "text_encoders, vae, loras, controlnet, upscale_models, checkpoints, "
                "embeddings, or 'all' for everything."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Model category to list, or 'all'",
                        "default": "all",
                    },
                },
            },
        ),
        Tool(
            name="comfyui_generate",
            description=(
                "Generate or edit an image. This is the main high-level tool. "
                "For text-to-image: provide prompt + quality. "
                "For image editing: provide prompt + input_image_path. "
                "For upscaling: use template='img_upscale_z_image_turbo' + input_image_path. "
                "Templates: txt2img_z_image_turbo (fast), txt2img_flux1_dev (quality), "
                "txt2img_flux2_dev (best), img_edit_flux2_klein (edit), img_upscale_z_image_turbo (upscale)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Text description of the image to generate or edit instruction",
                    },
                    "template": {
                        "type": "string",
                        "description": "Template name or 'auto'. Auto picks based on whether input_image_path is provided.",
                        "default": "auto",
                    },
                    "input_image_path": {
                        "type": "string",
                        "description": "Path to input image for editing/upscaling. If provided, auto-selects an img2img template.",
                        "default": "",
                    },
                    "width": {
                        "type": "integer",
                        "description": "Image width in pixels (default: 1024, ignored for img2img)",
                        "default": 1024,
                    },
                    "height": {
                        "type": "integer",
                        "description": "Image height in pixels (default: 1024, ignored for img2img)",
                        "default": 1024,
                    },
                    "seed": {
                        "type": "integer",
                        "description": "Random seed (-1 for random)",
                        "default": -1,
                    },
                    "steps": {
                        "type": "integer",
                        "description": "Number of sampling steps (-1 for template default)",
                        "default": -1,
                    },
                    "cfg": {
                        "type": "number",
                        "description": "CFG scale (-1 for template default)",
                        "default": -1,
                    },
                    "denoise": {
                        "type": "number",
                        "description": "Denoise strength for img2img/upscale (0.0-1.0, -1 for template default)",
                        "default": -1,
                    },
                    "quality": {
                        "type": "string",
                        "description": "Quality preset: 'fast', 'balanced' (default), or 'quality'",
                        "default": "balanced",
                        "enum": ["fast", "balanced", "quality"],
                    },
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="comfyui_open_image",
            description=(
                "Open a generated image in the default browser or image viewer. "
                "Pass the file path returned by comfyui_generate."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Local file path or ComfyUI URL to open",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="comfyui_queue_workflow",
            description=(
                "Low-level tool: submit a raw ComfyUI API-format workflow JSON. "
                "Does NOT wait for completion. Use comfyui_get_result to poll for results."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow": {
                        "type": "object",
                        "description": "Raw API-format workflow JSON (node_id -> {class_type, inputs})",
                    },
                },
                "required": ["workflow"],
            },
        ),
        Tool(
            name="comfyui_get_result",
            description=(
                "Get the result of a previously queued workflow by prompt_id. "
                "Returns status (completed/pending/error) and output images."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt_id": {
                        "type": "string",
                        "description": "The prompt_id returned by comfyui_queue_workflow or comfyui_generate",
                    },
                },
                "required": ["prompt_id"],
            },
        ),
        Tool(
            name="comfyui_list_blueprints",
            description=(
                "List ComfyUI's built-in blueprint workflows. "
                "Blueprints are pre-made workflows for common tasks like text-to-image, "
                "image editing, video generation, upscaling, etc."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="comfyui_list_templates",
            description=(
                "List the plugin's custom workflow templates with their parameters and defaults. "
                "These are the templates used by comfyui_generate."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="comfyui_nodes",
            description=(
                "Search available ComfyUI node types. Returns node class names, categories, "
                "and input/output schemas. Use filter to search by name or category."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "string",
                        "description": "Search term to filter nodes by name, display_name, or category",
                        "default": "",
                    },
                },
            },
        ),
        Tool(
            name="comfyui_download_model",
            description=(
                "Download a model file from a URL (typically HuggingFace) to the correct "
                "ComfyUI models folder. Always confirm with the user before downloading."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Direct download URL (e.g., HuggingFace resolve URL)",
                    },
                    "category": {
                        "type": "string",
                        "description": "Model category folder: diffusion_models, loras, controlnet, upscale_models, text_encoders, vae, embeddings",
                    },
                    "filename": {
                        "type": "string",
                        "description": "Filename to save as (optional, derived from URL if not specified)",
                        "default": "",
                    },
                },
                "required": ["url", "category"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Route tool calls to their implementations."""
    try:
        if name == "comfyui_status":
            return await _handle_status()
        elif name == "comfyui_start":
            return await _handle_start(arguments)
        elif name == "comfyui_models":
            return await _handle_models(arguments)
        elif name == "comfyui_generate":
            return await _handle_generate(arguments)
        elif name == "comfyui_open_image":
            return await _handle_open_image(arguments)
        elif name == "comfyui_queue_workflow":
            return await _handle_queue_workflow(arguments)
        elif name == "comfyui_get_result":
            return await _handle_get_result(arguments)
        elif name == "comfyui_list_blueprints":
            return await _handle_list_blueprints()
        elif name == "comfyui_list_templates":
            return await _handle_list_templates()
        elif name == "comfyui_nodes":
            return await _handle_nodes(arguments)
        elif name == "comfyui_download_model":
            return await _handle_download_model(arguments)
        else:
            return _text(f"Unknown tool: {name}")
    except Exception as e:
        return _text(json.dumps({"error": str(e)}, indent=2))


async def _handle_status() -> list[TextContent]:
    """Check ComfyUI status."""
    running = await client.is_running()
    if not running:
        msg = "ComfyUI is not running."
        if not COMFYUI_ROOT:
            msg += " COMFYUI_ROOT is not set - set it to your ComfyUI installation path."
        else:
            msg += " Use comfyui_start to launch it."
        return _text(json.dumps({
            "running": False,
            "comfyui_root": COMFYUI_ROOT or "(not set)",
            "message": msg,
        }, indent=2))

    stats = await client.get_system_stats()
    queue = await client.get_queue_info()

    # Extract useful info
    devices = stats.get("devices", [])
    gpu_info = {}
    if devices:
        dev = devices[0]
        gpu_info = {
            "name": dev.get("name", "Unknown"),
            "type": dev.get("type", "Unknown"),
            "vram_total_mb": round(dev.get("vram_total", 0) / 1024 / 1024),
            "vram_free_mb": round(dev.get("vram_free", 0) / 1024 / 1024),
            "torch_vram_total_mb": round(dev.get("torch_vram_total", 0) / 1024 / 1024),
            "torch_vram_free_mb": round(dev.get("torch_vram_free", 0) / 1024 / 1024),
        }

    result = {
        "running": True,
        "gpu": gpu_info,
        "queue_running": len(queue.get("queue_running", [])),
        "queue_pending": len(queue.get("queue_pending", [])),
    }
    return _text(json.dumps(result, indent=2))


async def _handle_start(arguments: dict) -> list[TextContent]:
    """Start ComfyUI process."""
    if not COMFYUI_ROOT:
        return _text(json.dumps({
            "error": "COMFYUI_ROOT not set. Set the environment variable to your ComfyUI installation path.",
        }, indent=2))

    # Check if already running
    if await client.is_running():
        return _text(json.dumps({
            "already_running": True,
            "message": "ComfyUI is already running.",
        }, indent=2))

    wait_seconds = arguments.get("wait_seconds", 60)
    main_py = os.path.join(COMFYUI_ROOT, "ComfyUI", "main.py")

    if not os.path.exists(main_py):
        return _text(json.dumps({
            "error": f"ComfyUI main.py not found at {main_py}. Check COMFYUI_ROOT setting.",
        }, indent=2))

    # Detect platform and find Python executable
    is_windows = sys.platform == "win32"
    python_exe = None
    cmd_args = []

    # Windows standalone build (embedded Python)
    embedded_python = os.path.join(COMFYUI_ROOT, "python_embeded", "python.exe")
    if is_windows and os.path.exists(embedded_python):
        python_exe = embedded_python
        cmd_args = [python_exe, "-s", main_py, "--windows-standalone-build"]
    else:
        # Linux/Mac or non-embedded: try venv, then system python
        venv_python = os.path.join(COMFYUI_ROOT, "venv", "bin", "python")
        if not is_windows and os.path.exists(venv_python):
            python_exe = venv_python
        else:
            python_exe = sys.executable  # fallback to current python
        cmd_args = [python_exe, main_py]

    env = os.environ.copy()
    env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True,garbage_collection_threshold:0.8"
    env["NVIDIA_TF32_OVERRIDE"] = "1"
    env["CUDA_MODULE_LOADING"] = "LAZY"

    try:
        kwargs = {
            "env": env,
            "cwd": COMFYUI_ROOT,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if is_windows:
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        else:
            kwargs["start_new_session"] = True

        proc = subprocess.Popen(cmd_args, **kwargs)
    except Exception as e:
        return _text(json.dumps({
            "error": f"Failed to start ComfyUI: {e}",
        }, indent=2))

    # Poll until ready
    import asyncio
    start = time.time()
    while time.time() - start < wait_seconds:
        await asyncio.sleep(2)
        if await client.is_running():
            return _text(json.dumps({
                "started": True,
                "pid": proc.pid,
                "elapsed_seconds": round(time.time() - start, 1),
                "message": "ComfyUI is now running and ready.",
            }, indent=2))

    return _text(json.dumps({
        "started": False,
        "pid": proc.pid,
        "message": f"ComfyUI process started (PID {proc.pid}) but not yet responding after {wait_seconds}s. It may still be loading models.",
    }, indent=2))


async def _handle_models(arguments: dict) -> list[TextContent]:
    """List installed models."""
    category = arguments.get("category", "all")

    if category == "all":
        models = await client.get_all_models()
    else:
        try:
            model_list = await client.get_models(category)
            models = {category: model_list}
        except Exception as e:
            return _text(json.dumps({"error": str(e)}, indent=2))

    return _text(json.dumps(models, indent=2))


async def _handle_generate(arguments: dict) -> list[TextContent]:
    """Generate or edit an image using a workflow template."""
    prompt_text = arguments.get("prompt", "")
    if not prompt_text:
        return _text(json.dumps({"error": "prompt is required"}, indent=2))

    # Check ComfyUI is running
    if not await client.is_running():
        return _text(json.dumps({
            "error": "ComfyUI is not running. Use comfyui_start first.",
        }, indent=2))

    input_image_path = arguments.get("input_image_path", "")

    # Select template
    template_name = arguments.get("template", "auto")
    quality = arguments.get("quality", "balanced")

    if template_name == "auto":
        has_input = bool(input_image_path)
        template_name = templates.auto_select(
            has_input_image=has_input,
            quality=quality,
        )
        if not template_name:
            return _text(json.dumps({
                "error": "No templates available. Check the templates/ directory.",
            }, indent=2))

    # Check if template requires models that might need downloading
    template_info = templates.get_template(template_name)
    if template_info:
        meta_downloads = template_info.parameters  # check _meta for model_downloads
        # We store model_downloads in the raw JSON _meta, but TemplateInfo doesn't have it
        # Just proceed - the user will get a ComfyUI error if model is missing

    # Build params
    seed = arguments.get("seed", -1)
    if seed == -1:
        seed = random.randint(1, 2**32 - 1)

    params = {
        "prompt": prompt_text,
        "width": arguments.get("width", 1024),
        "height": arguments.get("height", 1024),
        "seed": seed,
        "steps": arguments.get("steps", -1),
        "cfg": arguments.get("cfg", -1),
        "denoise": arguments.get("denoise", -1),
    }

    # Handle input image upload for img2img/edit/upscale templates
    if input_image_path:
        if not os.path.exists(input_image_path):
            # Try relative to ComfyUI output dir
            alt_path = os.path.join(COMFYUI_ROOT, "ComfyUI", "output", input_image_path)
            if os.path.exists(alt_path):
                input_image_path = alt_path
            else:
                return _text(json.dumps({
                    "error": f"Input image not found: {input_image_path}",
                }, indent=2))

        try:
            upload_result = await client.upload_image(input_image_path)
            uploaded_name = upload_result.get("name", "")
            if not uploaded_name:
                return _text(json.dumps({
                    "error": "Image upload failed - no filename returned",
                }, indent=2))
            params["input_image"] = uploaded_name
        except Exception as e:
            return _text(json.dumps({
                "error": f"Image upload failed: {e}",
            }, indent=2))

    # Fill template
    try:
        workflow = templates.fill_template(template_name, params)
    except ValueError as e:
        return _text(json.dumps({"error": str(e)}, indent=2))

    # Submit and wait
    result = await client.queue_and_wait(workflow)

    # Add metadata
    result["template_used"] = template_name
    result["seed_used"] = seed
    result["parameters"] = {
        "prompt": prompt_text,
        "width": params["width"],
        "height": params["height"],
        "seed": seed,
    }

    # Provide helpful summary
    if result.get("status") == "completed" and result.get("images"):
        img = result["images"][0]
        result["summary"] = (
            f"Image generated successfully using '{template_name}' template. "
            f"File: {img['filename']} | Seed: {seed} | "
            f"Use comfyui_open_image to view it."
        )
    elif result.get("status") == "error":
        result["summary"] = f"Generation failed: {result.get('error', 'Unknown error')}"

    return _text(json.dumps(result, indent=2))


async def _handle_open_image(arguments: dict) -> list[TextContent]:
    """Open an image in the browser/viewer."""
    path = arguments.get("path", "")
    if not path:
        return _text(json.dumps({"error": "path is required"}, indent=2))

    # Normalize path
    path = path.replace("/", os.sep).replace("\\", os.sep)

    try:
        if path.startswith("http"):
            webbrowser.open(path)
        elif os.path.exists(path):
            os.startfile(path)
        else:
            # Try as a filename in the output directory
            output_path = os.path.join(COMFYUI_ROOT, "ComfyUI", "output", path)
            if os.path.exists(output_path):
                os.startfile(output_path)
            else:
                return _text(json.dumps({
                    "error": f"File not found: {path}",
                }, indent=2))

        return _text(json.dumps({
            "opened": True,
            "path": path,
        }, indent=2))
    except Exception as e:
        return _text(json.dumps({"error": str(e)}, indent=2))


async def _handle_queue_workflow(arguments: dict) -> list[TextContent]:
    """Submit a raw workflow without waiting."""
    workflow = arguments.get("workflow")
    if not workflow:
        return _text(json.dumps({"error": "workflow is required"}, indent=2))

    if not await client.is_running():
        return _text(json.dumps({"error": "ComfyUI is not running."}, indent=2))

    result = await client.queue_prompt(workflow)
    return _text(json.dumps(result, indent=2))


async def _handle_get_result(arguments: dict) -> list[TextContent]:
    """Get results for a prompt_id."""
    prompt_id = arguments.get("prompt_id", "")
    if not prompt_id:
        return _text(json.dumps({"error": "prompt_id is required"}, indent=2))

    result = await client._collect_results(prompt_id)
    return _text(json.dumps(result, indent=2))


async def _handle_list_blueprints() -> list[TextContent]:
    """List ComfyUI's built-in blueprints."""
    blueprints_dir = os.path.join(COMFYUI_ROOT, "ComfyUI", "blueprints")
    if not os.path.exists(blueprints_dir):
        return _text(json.dumps({"error": "Blueprints directory not found"}, indent=2))

    blueprints = []
    for f in sorted(os.listdir(blueprints_dir)):
        if f.endswith(".json"):
            name = f.replace(".json", "")
            # Try to extract category from the file
            category = ""
            try:
                with open(os.path.join(blueprints_dir, f), "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    defs = data.get("definitions", {})
                    subgraphs = defs.get("subgraphs", [])
                    if subgraphs:
                        category = subgraphs[0].get("category", "")
            except Exception:
                pass
            blueprints.append({"name": name, "category": category, "filename": f})

    return _text(json.dumps({"blueprints": blueprints, "count": len(blueprints)}, indent=2))


async def _handle_list_templates() -> list[TextContent]:
    """List plugin templates."""
    template_list = templates.list_templates()
    return _text(json.dumps({"templates": template_list, "count": len(template_list)}, indent=2))


async def _handle_nodes(arguments: dict) -> list[TextContent]:
    """Search available node types."""
    if not await client.is_running():
        return _text(json.dumps({"error": "ComfyUI is not running."}, indent=2))

    filter_str = arguments.get("filter", "")
    nodes = await client.get_object_info(filter_str)

    # Truncate to avoid overwhelming context
    result = []
    for class_type, info in list(nodes.items())[:50]:
        input_types = info.get("input", {})
        # Summarize inputs
        required = {}
        for k, v in input_types.get("required", {}).items():
            if isinstance(v, list) and v:
                required[k] = v[0] if isinstance(v[0], str) else str(v[0])[:50]
            else:
                required[k] = str(v)[:50]

        result.append({
            "class_type": class_type,
            "display_name": info.get("display_name", class_type),
            "category": info.get("category", ""),
            "inputs": required,
            "outputs": info.get("output", []),
        })

    return _text(json.dumps({
        "nodes": result,
        "count": len(result),
        "total_available": len(nodes),
        "filtered": bool(filter_str),
    }, indent=2))


async def _handle_download_model(arguments: dict) -> list[TextContent]:
    """Download a model file to the correct ComfyUI folder."""
    url = arguments.get("url", "")
    category = arguments.get("category", "")
    filename = arguments.get("filename", "")

    if not url or not category:
        return _text(json.dumps({"error": "url and category are required"}, indent=2))

    # Derive filename from URL if not provided
    if not filename:
        filename = url.split("/")[-1].split("?")[0]
        if not filename:
            return _text(json.dumps({"error": "Could not derive filename from URL. Please provide filename."}, indent=2))

    # Target path
    target_dir = os.path.join(COMFYUI_ROOT, "ComfyUI", "models", category)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    target_path = os.path.join(target_dir, filename)

    if os.path.exists(target_path):
        return _text(json.dumps({
            "already_exists": True,
            "path": target_path,
            "message": f"Model '{filename}' already exists in {category}/",
        }, indent=2))

    # Download with progress
    try:
        import httpx
        async with httpx.AsyncClient(follow_redirects=True, timeout=600.0) as dl_client:
            async with dl_client.stream("GET", url) as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length", 0))
                downloaded = 0
                with open(target_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                        f.write(chunk)
                        downloaded += len(chunk)

        size_mb = os.path.getsize(target_path) / 1024 / 1024
        return _text(json.dumps({
            "downloaded": True,
            "filename": filename,
            "category": category,
            "path": target_path,
            "size_mb": round(size_mb, 1),
            "message": f"Downloaded '{filename}' ({size_mb:.1f} MB) to {category}/",
        }, indent=2))
    except Exception as e:
        # Clean up partial download
        if os.path.exists(target_path):
            os.remove(target_path)
        return _text(json.dumps({"error": f"Download failed: {e}"}, indent=2))


async def main():
    """Run the MCP server via stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
