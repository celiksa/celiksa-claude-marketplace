---
description: "ComfyUI management - status, models, templates, blueprints, start"
argument-hint: "[status|models|templates|blueprints|nodes|start]"
---

# /comfyui

Manage the local ComfyUI installation.

## Subcommands

Route based on the argument provided:

- **status** (or no argument): Call `comfyui_status` and report GPU, VRAM, and queue info.
- **models**: Call `comfyui_models` with category="all" and display installed models by category.
- **templates**: Call `comfyui_list_templates` and show available generation templates with their parameters.
- **blueprints**: Call `comfyui_list_blueprints` and show built-in ComfyUI workflow blueprints.
- **nodes [filter]**: Call `comfyui_nodes` with the filter term to search available node types.
- **start**: Call `comfyui_start` to launch ComfyUI if it's not running.

## Examples

- `/comfyui status` - Check if ComfyUI is running
- `/comfyui models` - List all installed models
- `/comfyui templates` - Show available workflow templates
- `/comfyui blueprints` - Show built-in blueprint workflows
- `/comfyui nodes sampler` - Search for sampler-related nodes
- `/comfyui start` - Start ComfyUI
