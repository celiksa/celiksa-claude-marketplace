---
name: comfyui-models
description: Use when the user asks about available models, which model to use, recommended settings, model capabilities, or needs to download a new model for ComfyUI. Also use when a generation task requires a model that may not be installed.
---

# ComfyUI Model Knowledge & Recommendations

## Installed Models & Optimal Settings

### Diffusion Models (Image Generation)

| Model | File | Steps | CFG | Sampler | Scheduler | Speed | Quality |
|-------|------|-------|-----|---------|-----------|-------|---------|
| Z-Image-Turbo | z_image_turbo_nvfp4.safetensors | 4 | 1 | res_multistep | simple | ~3-5s | Good |
| Flux 1 Dev | flux1-dev-nvfp4.safetensors | 20 | 1 | euler | simple | ~30-60s | Excellent |
| Flux 2 Dev | flux2-dev-nvfp4.safetensors | 20 | 5 | euler | simple | ~30-60s | Best |

### Text Encoders

| Encoder | File | Used With | Notes |
|---------|------|-----------|-------|
| CLIP-L | clip_l.safetensors | Flux 1 (DualCLIP) | Paired with T5-XXL |
| T5-XXL FP16 | t5xxl_fp16.safetensors | Flux 1 (DualCLIP) | Large, may need CPU offload |
| Qwen 3 4B | qwen_3_4b.safetensors | Z-Image-Turbo | CLIPLoader type=lumina2 |
| Mistral 3 Small | mistral_3_small_flux2_fp8.safetensors | Flux 2 | CLIPLoader type=flux2 |

### VAE

| VAE | File | Used With |
|-----|------|-----------|
| AE | ae.safetensors | Flux 1, Z-Image-Turbo |
| Flux 2 VAE | flux2-vae.safetensors | Flux 2 |

## Model Selection Guide

### When to use which model:

**Z-Image-Turbo** (default, fastest):
- Quick iterations and drafts
- Exploring compositions and ideas
- When speed matters more than absolute quality
- Uses: UNETLoader + ModelSamplingAuraFlow(shift=3) + CLIPLoader(type=lumina2)

**Flux 1 Dev** (high quality):
- Detailed, photorealistic images
- Complex scenes with many elements
- When quality matters and you can wait 30-60s
- Uses: UNETLoader + DualCLIPLoader(type=flux) + CLIPTextEncodeFlux(guidance=3.5)
- Note: guidance parameter controls prompt adherence (3.5 default, lower=more creative, higher=more literal)

**Flux 2 Dev** (latest/best quality):
- Best text rendering in images
- Latest model quality
- Complex prompts with nuanced descriptions
- Uses: UNETLoader + CLIPLoader(type=flux2) + CLIPTextEncode

## Hardware Constraints

- **GPU**: 8GB VRAM (NVIDIA RTX 3070 Laptop)
- **RAM**: 64GB system memory
- All diffusion models use NV FP4 quantization to fit in 8GB VRAM
- Text encoders can be offloaded to CPU if VRAM is tight
- Prefer NV FP4 > FP8 > BF16 quantization order

## Dynamic Model Recommendations

When a user needs a model that isn't installed, follow this process:

1. **Identify the need**: What task requires a new model? (LoRA, ControlNet, upscaler, video, etc.)
2. **Research**: Use web search to find the best model for the task, filtering for:
   - 8GB VRAM compatibility (FP4/FP8 quantized preferred)
   - ComfyUI compatibility (must have a node that can load it)
   - Community-validated quality
3. **Present recommendation**: Tell the user the model name, size, VRAM requirements, and download URL
4. **Download**: After user confirms, use `comfyui_download_model` with the HuggingFace resolve URL

### Common model categories to recommend:

**LoRAs** (~50-300MB, always fit in VRAM):
- Style LoRAs for specific artistic styles
- Quality enhancement LoRAs
- Character/subject LoRAs
- Folder: `loras/`

**ControlNet** (~500MB-2GB):
- Canny edge detection → guided composition
- Depth maps → 3D-aware generation
- Pose estimation → human pose control
- Folder: `controlnet/`

**Upscale Models** (~20-60MB, tiny):
- Real-ESRGAN x4 for photorealistic upscaling
- Folder: `upscale_models/`

**Video Models** (large, need FP8/FP4):
- Wan 2.2 for text-to-video
- LTX 2.0 for video generation
- Folder: `diffusion_models/`

## Prompt Tips Per Model

**All Flux models**: Respond well to natural language descriptions. No negative prompts needed (they're ignored). Be descriptive about style, lighting, composition.

**Z-Image-Turbo**: Shorter, focused prompts work well. Good with style keywords.

**Flux 1 Dev**: Use both CLIP-L (short, keyword-style) and T5-XXL (long, descriptive) prompts via CLIPTextEncodeFlux. The `guidance` parameter (default 3.5) controls prompt adherence. Lower (2.0) = more creative, higher (5.0) = more literal.

**Flux 2 Dev**: Best at following complex, detailed prompts. Excellent text rendering - if you need text in the image, use this model.
