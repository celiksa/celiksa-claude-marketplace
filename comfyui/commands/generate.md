---
description: "Generate an image from a text description using ComfyUI"
argument-hint: "[description of what you want to generate]"
---

# /generate

Generate an image using the local ComfyUI installation.

## Instructions

1. First call `comfyui_status` to check if ComfyUI is running. If not, offer to start it with `comfyui_start`.

2. Take the user's description and enhance it into an effective generation prompt:
   - Be descriptive: subject, style, lighting, composition, mood
   - Add quality cues if appropriate: "highly detailed", "professional", "cinematic lighting"
   - Flux models respond well to natural language descriptions

3. Determine quality level from the user's intent:
   - Quick/fast/draft requests → quality="fast"
   - High quality/best/detailed/final requests → quality="quality"
   - Default → quality="balanced"

4. Call `comfyui_generate` with the enhanced prompt and appropriate quality setting.

5. When the result comes back, call `comfyui_open_image` to display it.

6. Report: the filename, seed (for reproduction), template used, and time taken.

7. Ask if the user wants any adjustments.
