---
name: generate
description: Use when the user wants to generate, create, or make an image, picture, photo, artwork, or any visual content using ComfyUI. Also use when the user asks to edit, modify, upscale, or transform an existing image.
---

# ComfyUI Image Generation

Generate images from natural language using the local ComfyUI installation.

## Process

Follow these steps in order:

### 1. Check ComfyUI Status
Always call `comfyui_status` first. If ComfyUI is not running, ask the user if they want to start it, then call `comfyui_start`.

### 2. Understand the Request
Parse what the user wants:
- **Text-to-image**: User describes an image to create from scratch → use txt2img templates
- **Image editing**: User wants to modify an existing image → use `img_edit_flux2_klein` template with `input_image_path`
- **Upscaling**: User wants to increase image resolution → use `img_upscale_z_image_turbo` template with `input_image_path`

For editing/upscaling, you need the path to an existing image. This can be:
- A previously generated image (from comfyui_generate output path)
- A file path the user provides
- A file in ComfyUI's output/ directory

### 3. Craft the Prompt
Enhance the user's description into an effective generation prompt:
- Be descriptive: include subject, style, lighting, composition, mood
- Flux models respond well to natural language descriptions
- No negative prompts needed for Flux/Z-Image-Turbo (they are ignored)
- Include artistic style if relevant: "oil painting", "photograph", "digital art", "watercolor"
- Include quality cues: "highly detailed", "professional", "cinematic lighting"

### 4. Select Template & Quality
Use the `quality` parameter in `comfyui_generate`:
- **"fast"** → Z-Image-Turbo (4 steps, ~3-5 seconds). Best for quick iterations, drafts, exploring ideas.
- **"balanced"** (default) → Z-Image-Turbo. Good enough for most requests.
- **"quality"** → Flux 1 Dev or Flux 2 Dev (20 steps, ~30-60 seconds). Best for final output, detailed work.

If the user asks for "quick", "fast", "draft" → use "fast"
If the user asks for "high quality", "best", "detailed", "final" → use "quality"
Otherwise → use "balanced"

### 5. Set Parameters
- **Size**: Default 1024x1024. For landscape: 1280x768 or 1344x768. For portrait: 768x1280 or 768x1344.
- **Seed**: Leave as -1 (random) unless user wants to reproduce a specific result.
- **Steps/CFG**: Leave as -1 to use template defaults. Only override if user specifically asks.

### 6. Generate
Call `comfyui_generate` with the assembled parameters.

### 7. Present Results
After generation completes:
1. Report the result: filename, seed used, template used, time taken
2. Call `comfyui_open_image` with the image path to display it
3. Mention the seed so the user can reproduce the exact result later

### 8. Iterate
If the user wants changes:
- **Same composition, different style**: Keep the seed, change the prompt
- **Completely different result**: Use seed=-1
- **Minor tweaks**: Keep seed and adjust prompt slightly
- **Higher quality version**: Keep same prompt/seed, switch to quality template

## Available Templates

| Template | Model | Speed | Best For |
|----------|-------|-------|----------|
| txt2img_z_image_turbo | Z-Image-Turbo (NV FP4) | ~3-5s | Quick iterations, drafts |
| txt2img_flux1_dev | Flux 1 Dev (NV FP4) | ~30-60s | High-quality final images |
| txt2img_flux2_dev | Flux 2 Dev (NV FP4) | ~30-60s | Latest quality, text rendering |
| img_edit_flux2_klein | Flux 2 Klein 4B (FP8) | ~20-40s | Image editing with reference conditioning |
| img_upscale_z_image_turbo | Z-Image-Turbo + RealESRGAN | ~10-20s | AI upscaling with quality enhancement |
| txt2vid_wan22 | Wan 2.2 14B (FP8) | ~2-5 min | Text-to-video (81 frames, 5s @ 16fps) |
| canny2img_z_image_turbo | Z-Image-Turbo + ControlNet | ~5-10s | Edge-guided image generation |
| pose2img_z_image_turbo | Z-Image-Turbo + ControlNet | ~5-10s | Pose-guided image generation |

### Video Notes
- **txt2vid_wan22**: Requires 6 model files (~28GB total). Very VRAM-intensive, needs CPU offloading.
- Dual-pass pipeline: high-noise model (2 steps) → low-noise model (2 steps) with LightX2V LoRAs
- Default: 640x640, 81 frames (5 seconds at 16fps). Reduce `length` for shorter/faster videos.
- Use `comfyui_download_model` to download all required Wan 2.2 models before first use.

### ControlNet Notes
- **canny2img / pose2img**: Require `Z-Image-Turbo-Fun-Controlnet-Union.safetensors` (~1.3GB download)
- Canny: extracts edges from input image, generates new image following edge structure
- Pose: uses input image directly as pose/structure guide
- `strength` parameter (default 1.0): lower = more creative freedom, higher = stricter adherence to control image
- 9 steps default (more than standard Z-Image-Turbo's 4 steps for better ControlNet quality)

### Image Editing Notes
- **img_edit_flux2_klein**: Requires `flux-2-klein-base-4b-fp8.safetensors` (may need download)
- Uses reference conditioning: preserves original image structure while applying edits
- Prompt describes the desired edit, not the entire image

### Upscaling Notes
- **img_upscale_z_image_turbo**: Requires `RealESRGAN_x4plus.safetensors` (~64MB, may need download)
- Pipeline: scale input → RealESRGAN 4x upscale → scale down 0.5x → Z-Image-Turbo refinement
- `denoise` parameter (default 0.33) controls how much AI refinement is applied
- Lower denoise (0.1-0.2) = closer to original, higher (0.4-0.6) = more AI enhancement

## Common Sizes

| Aspect | Resolution | Use Case |
|--------|-----------|----------|
| 1:1 | 1024x1024 | Default, social media |
| 16:9 | 1344x768 | Landscape, wallpaper |
| 9:16 | 768x1344 | Portrait, phone wallpaper |
| 3:2 | 1216x832 | Photography style |
| 2:3 | 832x1216 | Portrait photography |

## Important Notes
- All models use 8GB VRAM with NV FP4 quantization
- Only one generation can run at a time (ComfyUI queues them)
- If generation fails, check comfyui_status for GPU/VRAM issues
- Seeds are reproducible: same seed + same prompt + same template = same image
