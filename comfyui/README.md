# ComfyUI Plugin for Claude Code

Turn Claude Code into a full AI image generation studio powered by your local [ComfyUI](https://github.com/comfyanonymous/ComfyUI) installation.

Describe what you want in plain English - Claude selects the right model, builds the optimal workflow, sends it to ComfyUI, monitors progress, and opens the result. No node wiring required.

## What You Can Do

- **"Generate a photo of a cat in a top hat"** - Text-to-image with automatic model/template selection
- **"Make this image look like a watercolor painting"** - Edit existing images with AI
- **"Upscale this image to 4x"** - AI-enhanced upscaling with RealESRGAN + refinement
- **"Create a 5-second video of a cat playing piano"** - Text-to-video with Wan 2.2
- **"Generate an image following this pose"** - ControlNet-guided generation
- **"What models do I have installed?"** - Full model and system management

## Architecture

```
You (natural language) --> Claude Code + Skills --> MCP Server (Python) --> ComfyUI API (localhost:8188)
```

The plugin has three layers:

1. **MCP Server** (`server/`) - A Python server that wraps ComfyUI's REST/WebSocket API as 11 Claude Code tools. Handles workflow submission, progress monitoring, result retrieval, model downloads, and ComfyUI process management.

2. **Skills** (`skills/`) - Markdown guides that auto-trigger when relevant. They teach Claude how to craft effective prompts, pick the right model/template, set optimal parameters, and iterate on results.

3. **Slash Commands** (`commands/`) - Quick-access entry points: `/comfyui:generate` for image creation, `/comfyui:comfyui` for system management.

## Installation

### Prerequisites

- **ComfyUI** installed locally ([install guide](https://github.com/comfyanonymous/ComfyUI#installing))
- **uv** Python package manager ([install guide](https://docs.astral.sh/uv/getting-started/installation/))
- **Claude Code** CLI, desktop, or web app

### Install via Marketplace

Add to your `~/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "celiksa-claude-marketplace": {
      "source": {
        "source": "github",
        "repo": "celiksa/celiksa-claude-marketplace"
      }
    }
  },
  "enabledPlugins": {
    "comfyui@celiksa-claude-marketplace": true
  }
}
```

Restart Claude Code and approve the plugin when prompted.

### ComfyUI Path Configuration

The plugin auto-detects ComfyUI in common locations:

- `~/ComfyUI`, `~/AI/ComfyUI`
- `C:/ComfyUI`, `D:/ComfyUI`, `C:/AI/ComfyUI`, `D:/AI/ComfyUI` (Windows)
- `C:/StabilityMatrix/Packages/ComfyUI` (StabilityMatrix)
- `/opt/ComfyUI` (Linux)

If your installation is elsewhere, set the `COMFYUI_ROOT` environment variable:

```bash
# In your .bashrc / .zshrc / PowerShell profile
export COMFYUI_ROOT="/path/to/your/ComfyUI"
```

## Usage

### Quick Start

```
> generate a beautiful sunset over mountains
```

Claude will:
1. Check if ComfyUI is running (offer to start it if not)
2. Enhance your prompt for optimal results
3. Select the best template and model
4. Generate the image and open it

### Slash Commands

```
/comfyui:generate a cyberpunk cityscape at night     # Generate an image
/comfyui:comfyui status                               # Check GPU, VRAM, queue
/comfyui:comfyui models                               # List installed models
/comfyui:comfyui templates                            # Show available templates
/comfyui:comfyui blueprints                           # Show ComfyUI's built-in blueprints
/comfyui:comfyui start                                # Launch ComfyUI
```

### Quality Presets

| Preset | Model | Speed | When to Use |
|--------|-------|-------|-------------|
| `fast` | Z-Image-Turbo | ~3-5s | Quick iterations, exploring ideas |
| `balanced` | Z-Image-Turbo (default) | ~3-5s | General use |
| `quality` | Flux 2 Dev | ~30-60s | Final output, detailed work, text in images |

```
> generate a portrait, quality mode
> generate quick drafts of 5 logo concepts
```

### Image Editing

Provide a path to an existing image:

```
> edit D:/photos/landscape.png to add dramatic storm clouds
> make this image look like an oil painting: D:/AI/ComfyUI/ComfyUI/output/comfyui-plugin_00001_.png
```

### Upscaling

```
> upscale D:/AI/ComfyUI/ComfyUI/output/comfyui-plugin_00001_.png
```

The upscale pipeline: RealESRGAN 4x upscale + Z-Image-Turbo AI refinement. Control the `denoise` parameter (default 0.33) - lower preserves more detail, higher adds more AI enhancement.

### Video Generation

```
> create a video of a cat playing piano
```

Uses Wan 2.2 with dual-pass pipeline (4 steps with LightX2V acceleration). Default: 640x640, 81 frames (~5 seconds at 16fps). Note: requires ~28GB of model downloads.

### ControlNet

```
> generate an image following the edges from D:/photos/building.png, make it a futuristic city
> generate using the pose from D:/photos/dancer.png, in a fantasy art style
```

Canny (edge-guided) and Pose (structure-guided) templates available using Z-Image-Turbo + ControlNet Union.

### Custom Workflows

For advanced users, build workflows from scratch:

```
> I need a workflow that loads a LoRA, applies ControlNet, and uses img2img with Flux 2
```

Claude uses the `workflow-builder` skill and `comfyui_nodes` tool to discover available nodes and construct custom API-format workflows.

## Workflow Templates

### Text-to-Image

| Template | Model | Steps | CFG | Sampler | Notes |
|----------|-------|-------|-----|---------|-------|
| `txt2img_z_image_turbo` | Z-Image-Turbo (NV FP4) | 4 | 1 | res_multistep | Fastest. Uses ModelSamplingAuraFlow(shift=3), CLIPLoader(lumina2) |
| `txt2img_flux1_dev` | Flux 1 Dev (NV FP4) | 20 | 1 | euler | High quality. Uses DualCLIPLoader(flux), CLIPTextEncodeFlux(guidance=3.5) |
| `txt2img_flux2_dev` | Flux 2 Dev (NV FP4) | 20 | 5 | euler | Best quality. Uses CLIPLoader(flux2), best text rendering |

### Image Processing

| Template | Model | Description | Extra Models Needed |
|----------|-------|-------------|-------------------|
| `img_edit_flux2_klein` | Flux 2 Klein 4B | Reference conditioning - edit while preserving structure | `flux-2-klein-4b-nvfp4.safetensors` |
| `img_upscale_z_image_turbo` | Z-Image-Turbo + RealESRGAN | 4x upscale with AI refinement (denoise=0.33) | `RealESRGAN_x4plus.safetensors` (~64MB) |

### Video

| Template | Model | Description | Extra Models Needed |
|----------|-------|-------------|-------------------|
| `txt2vid_wan22` | Wan 2.2 14B (FP8) | Dual-pass: high-noise (2 steps) + low-noise (2 steps) with LightX2V LoRAs | 6 model files (~28GB total) |

### ControlNet

| Template | Model | Description | Extra Models Needed |
|----------|-------|-------------|-------------------|
| `canny2img_z_image_turbo` | Z-Image-Turbo + ControlNet Union | Extract edges, generate following edge structure | `Z-Image-Turbo-Fun-Controlnet-Union.safetensors` (~1.3GB) |
| `pose2img_z_image_turbo` | Z-Image-Turbo + ControlNet Union | Generate following pose/structure of input image | Same ControlNet Union model |

## MCP Tools

| Tool | Description |
|------|-------------|
| `comfyui_status` | Check if ComfyUI is running. Returns GPU name, VRAM total/free, queue status. Always call this first. |
| `comfyui_start` | Launch ComfyUI process. Auto-detects Windows standalone (python_embeded) or Linux/Mac venv. Polls until ready. |
| `comfyui_models` | List installed models by category (diffusion_models, text_encoders, vae, loras, controlnet, upscale_models, etc.). |
| `comfyui_generate` | **Main tool.** Takes a text prompt + optional parameters, selects template, fills parameters, submits to ComfyUI, waits for completion via WebSocket, returns output image paths. Supports input_image_path for editing/upscaling. |
| `comfyui_open_image` | Open a generated image in the default browser or image viewer. |
| `comfyui_queue_workflow` | Low-level: submit raw ComfyUI API-format workflow JSON. Does not wait for completion. |
| `comfyui_get_result` | Get results for a previously queued workflow by prompt_id. Returns status + output images. |
| `comfyui_list_blueprints` | List ComfyUI's 38+ built-in blueprint workflows with categories. |
| `comfyui_list_templates` | List this plugin's workflow templates with parameter schemas and defaults. |
| `comfyui_nodes` | Search available ComfyUI node types by name or category. Returns class_type, inputs, outputs. |
| `comfyui_download_model` | Download a model from HuggingFace (or any URL) to the correct ComfyUI models subfolder. |

## Skills

Skills auto-trigger based on what you ask Claude to do. You don't invoke them directly.

| Skill | Triggers When | What It Does |
|-------|--------------|--------------|
| `generate` | You ask to create, generate, edit, upscale, or transform any image | Guides Claude through the full workflow: check status, select template, craft prompt, set parameters, generate, present results, iterate |
| `comfyui-models` | You ask about models, settings, which model to use, or need a missing model | Provides model knowledge (optimal settings per model), recommends models for tasks, guides downloads |
| `workflow-builder` | You need a custom workflow, want to combine nodes, or ask about ComfyUI capabilities | Teaches Claude the API format, common node patterns, how to wire nodes, and how to submit custom workflows |

## How It Works Under the Hood

1. **Template System**: Workflows are pre-built API-format JSON files with a `_meta` key mapping parameter names to node/field paths. The template manager loads, fills, and strips `_meta` before submission.

2. **ComfyUI Client**: Async Python client using `httpx` + `websockets`. Connects to ComfyUI's WebSocket for real-time progress monitoring, falls back to polling if WebSocket fails.

3. **Auto-Detection**: On startup, the server scans common installation paths across Windows/Mac/Linux to find ComfyUI without requiring manual configuration.

4. **Model Downloads**: Templates include `model_downloads` metadata with HuggingFace URLs. When a template needs a model that isn't installed, Claude can download it via `comfyui_download_model`.

## File Structure

```
comfyui/
  .claude-plugin/plugin.json       # Plugin metadata
  .mcp.json                         # MCP server config (runs via uv)
  server/
    comfyui_mcp_server.py           # MCP server - 11 tool handlers (780 lines)
    comfyui_client.py               # Async HTTP/WebSocket client (309 lines)
    workflow_templates.py           # Template loading and parameter fill (170 lines)
    models.py                       # Data models (44 lines)
    pyproject.toml                  # Dependencies: mcp, httpx, websockets
  skills/
    generate/SKILL.md               # Generation guidance
    comfyui-models/SKILL.md         # Model knowledge base
    workflow-builder/SKILL.md       # Custom workflow building
  commands/
    generate.md                     # /comfyui:generate slash command
    comfyui.md                      # /comfyui:comfyui management command
  templates/
    txt2img_z_image_turbo.json      # 8 workflow templates
    txt2img_flux1_dev.json
    txt2img_flux2_dev.json
    img_edit_flux2_klein.json
    img_upscale_z_image_turbo.json
    txt2vid_wan22.json
    canny2img_z_image_turbo.json
    pose2img_z_image_turbo.json
```

## Compatibility

- **OS**: Windows, macOS, Linux
- **ComfyUI**: v0.18.x+ (tested with v0.18.1)
- **GPU**: Works with any VRAM size. Templates default to FP4/FP8 quantized models optimized for 8GB VRAM. Larger GPUs can use full-precision models.
- **Claude Code**: CLI, Desktop app, Web app (claude.ai/code), IDE extensions

## License

MIT
