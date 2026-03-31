# celiksa-claude-marketplace

Custom [Claude Code](https://docs.anthropic.com/en/docs/claude-code) plugins by celiksa.

## Installation

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

Restart Claude Code and approve the marketplace when prompted.

## Plugins

### comfyui

Natural-language image generation via local [ComfyUI](https://github.com/comfyanonymous/ComfyUI).

**Features:**
- 11 MCP tools (generate, status, models, queue, download, etc.)
- 8 workflow templates (text-to-image, image editing, upscaling, video, ControlNet)
- 3 skills (generation guidance, model knowledge, custom workflow building)
- 2 slash commands (`/generate`, `/comfyui`)

**Supported models:** Flux 1/2 Dev, Z-Image-Turbo, Wan 2.2, ControlNet Union

**Requirements:**
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) installed locally
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Set `COMFYUI_ROOT` environment variable to your ComfyUI installation path

See [comfyui/README.md](comfyui/README.md) for detailed documentation.

## Adding More Plugins

Each plugin lives in its own subdirectory with a `.claude-plugin/plugin.json`. New plugins are registered in `.claude-plugin/marketplace.json`.

## License

MIT
