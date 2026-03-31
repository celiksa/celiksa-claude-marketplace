# celiksa-claude-marketplace

A plugin marketplace for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) by [@celiksa](https://github.com/celiksa).

This marketplace provides plugins that extend Claude Code with specialized tools, skills, and commands. Each plugin integrates deeply with Claude Code's workflow - providing MCP tools for direct API access, skills for intelligent guidance, and slash commands for quick actions.

## Available Plugins

| Plugin | Description | Status |
|--------|-------------|--------|
| [comfyui](comfyui/) | Natural-language image generation via local ComfyUI | v0.1.0 |

## Installation

### Step 1: Add the marketplace

Add this to your Claude Code settings file (`~/.claude/settings.json` on Mac/Linux, `C:\Users\<you>\.claude\settings.json` on Windows):

```json
{
  "extraKnownMarketplaces": {
    "celiksa-claude-marketplace": {
      "source": {
        "source": "github",
        "repo": "celiksa/celiksa-claude-marketplace"
      }
    }
  }
}
```

### Step 2: Enable a plugin

In the same settings file, add the plugin(s) you want to enable:

```json
{
  "enabledPlugins": {
    "comfyui@celiksa-claude-marketplace": true
  }
}
```

### Step 3: Restart Claude Code

Restart Claude Code. You'll be prompted to approve the new marketplace and plugins. Once approved, the plugin's tools, skills, and slash commands become available in every session.

## Plugin Details

### comfyui - ComfyUI Image Generation

Turn Claude Code into a full AI image generation studio. Describe what you want in natural language, and Claude handles everything - selecting the right model, building the optimal workflow, submitting it to your local ComfyUI, and opening the result.

**What it provides:**
- **11 MCP tools** for full ComfyUI API control
- **8 workflow templates** covering text-to-image, image editing, upscaling, video generation, and ControlNet
- **3 skills** that auto-trigger to guide Claude through generation, model selection, and custom workflows
- **2 slash commands** (`/comfyui:generate`, `/comfyui:comfyui`)

**Supported models:** Flux 1 Dev, Flux 2 Dev, Z-Image-Turbo, Wan 2.2, ControlNet Union

**Requirements:** Local ComfyUI installation + [uv](https://docs.astral.sh/uv/) Python package manager

See [comfyui/README.md](comfyui/README.md) for full documentation.

## Marketplace Structure

```
celiksa-claude-marketplace/
  .claude-plugin/
    marketplace.json        # Plugin registry - lists all available plugins
  comfyui/                  # ComfyUI plugin
    .claude-plugin/
      plugin.json           # Plugin metadata (name, version, author)
    .mcp.json               # MCP server configuration
    server/                 # Python MCP server (ComfyUI API wrapper)
    skills/                 # Auto-triggered guidance for Claude
    commands/               # Slash commands (/generate, /comfyui)
    templates/              # ComfyUI workflow templates (JSON)
  <future-plugin>/          # Add more plugins here
```

## Adding a New Plugin

1. Create a subdirectory with your plugin name (e.g., `my-plugin/`)
2. Add `.claude-plugin/plugin.json` with metadata
3. Add skills, commands, MCP servers, or hooks as needed
4. Register it in `.claude-plugin/marketplace.json` at the root
5. Commit and push

## License

MIT
