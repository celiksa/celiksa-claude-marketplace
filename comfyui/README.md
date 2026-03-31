# ComfyUI Plugin for Claude Code

Natural-language image generation, editing, upscaling, video creation, and ControlNet-guided generation via your local [ComfyUI](https://github.com/comfyanonymous/ComfyUI) installation.

## Features

- **11 MCP Tools** - Full ComfyUI API integration (generate, status, models, queue, download, etc.)
- **8 Workflow Templates** - Text-to-image, image editing, upscaling, video, ControlNet
- **3 Skills** - Auto-triggered guidance for generation, model selection, and custom workflow building
- **2 Slash Commands** - `/generate` and `/comfyui`

### Templates

| Template | Type | Description |
|----------|------|-------------|
| `txt2img_z_image_turbo` | Text to Image | Fast generation (~3-5s, 4 steps) |
| `txt2img_flux1_dev` | Text to Image | High quality (Flux 1 Dev, 20 steps) |
| `txt2img_flux2_dev` | Text to Image | Best quality (Flux 2 Dev, 20 steps) |
| `img_edit_flux2_klein` | Image Editing | Edit images with Flux 2 Klein + reference conditioning |
| `img_upscale_z_image_turbo` | Upscaling | RealESRGAN 4x + AI refinement |
| `txt2vid_wan22` | Text to Video | Wan 2.2 dual-pass video generation |
| `canny2img_z_image_turbo` | ControlNet | Canny edge-guided generation |
| `pose2img_z_image_turbo` | ControlNet | Pose-guided generation |

## Installation

### Prerequisites

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) installed locally
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)

### Install the Plugin

Add this to your `~/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "comfyui-claude-plugin": {
      "source": {
        "source": "github",
        "repo": "celiksa/comfyui-claude-plugin"
      }
    }
  },
  "enabledPlugins": {
    "comfyui@comfyui-claude-plugin": true
  }
}
```

Restart Claude Code. You'll be prompted to approve the plugin.

### Configuration

Set the `COMFYUI_ROOT` environment variable to your ComfyUI installation path. Add it to your shell profile or to the plugin config:

**Option 1: Environment variable**
```bash
# In your .bashrc / .zshrc / shell profile
export COMFYUI_ROOT="/path/to/your/ComfyUI"
```

**Option 2: In your workspace `.mcp.json`**
```json
{
  "mcpServers": {
    "comfyui": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "<plugin-cache-path>/server", "python", "comfyui_mcp_server.py"],
      "env": {
        "COMFYUI_ROOT": "/path/to/your/ComfyUI"
      }
    }
  }
}
```

The plugin auto-detects common ComfyUI locations (`~/ComfyUI`, `~/AI/ComfyUI`, etc.) if the env var is not set.

## Usage

### Generate Images

Just describe what you want:

```
> Generate a majestic cat wearing a golden crown, cinematic lighting
```

Or use the slash command:

```
> /generate a sunset over snow-capped mountains
```

### Quality Presets

- **fast** (Z-Image-Turbo, ~3-5s): Quick iterations
- **balanced** (default): Auto-selects best speed/quality tradeoff
- **quality** (Flux Dev, ~30-60s): Best output

```
> Generate a portrait in high quality mode
```

### Image Editing

```
> Edit this image to make it look like a watercolor painting
> (provide input_image_path to a local file)
```

### Upscaling

```
> Upscale this image with template img_upscale_z_image_turbo
```

### Management

```
> /comfyui status    - Check GPU, VRAM, queue
> /comfyui models    - List installed models
> /comfyui templates - Show available templates
> /comfyui start     - Launch ComfyUI
```

## Models

The plugin works with whatever models you have installed in ComfyUI. The included templates are designed for:

| Model | Template(s) | Notes |
|-------|-------------|-------|
| Z-Image-Turbo (FP4) | txt2img, upscale, controlnet | Fastest, 4 steps |
| Flux 1 Dev (FP4) | txt2img | High quality, 20 steps |
| Flux 2 Dev (FP4) | txt2img, img_edit | Best quality, 20 steps |
| Wan 2.2 14B (FP8) | txt2vid | Video generation |

Some templates require additional model downloads (RealESRGAN, ControlNet Union, Flux 2 Klein, Wan 2.2 models). The plugin will tell you what's needed and can download them via `comfyui_download_model`.

## MCP Tools Reference

| Tool | Description |
|------|-------------|
| `comfyui_status` | Check ComfyUI running state, GPU/VRAM info |
| `comfyui_start` | Launch ComfyUI process |
| `comfyui_models` | List installed models by category |
| `comfyui_generate` | High-level: prompt to image with auto template selection |
| `comfyui_open_image` | Open result in browser/viewer |
| `comfyui_queue_workflow` | Low-level: submit raw API workflow JSON |
| `comfyui_get_result` | Get results for a queued workflow |
| `comfyui_list_blueprints` | List ComfyUI's built-in blueprints |
| `comfyui_list_templates` | List plugin's workflow templates |
| `comfyui_nodes` | Search available ComfyUI node types |
| `comfyui_download_model` | Download model from HuggingFace |

## License

MIT
