---
name: workflow-builder
description: Use when the user needs a custom ComfyUI workflow that doesn't match existing templates, wants to combine nodes in novel ways, or asks about ComfyUI nodes and capabilities. Also use when debugging or modifying existing workflows.
---

# ComfyUI Workflow Builder

Build custom ComfyUI workflows from individual nodes when no existing template fits the task.

## When to Use This Skill

- User wants a workflow that doesn't match any template (e.g., ControlNet + LoRA + inpainting)
- User asks to modify an existing workflow
- User wants to understand what nodes are available
- User needs a workflow for a new model or technique

## API Format

ComfyUI workflows for the `/prompt` API use this format:

```json
{
  "node_id": {
    "class_type": "NodeClassName",
    "inputs": {
      "param_name": value,
      "connected_input": ["other_node_id", output_index]
    }
  }
}
```

- **Node IDs** are strings (e.g., "1", "2", "my_node")
- **Direct values**: strings, numbers, booleans
- **Node connections**: `["source_node_id", output_index]` where output_index is 0-based

## Building a Workflow

### Step 1: Discover Nodes
Use `comfyui_nodes` with a filter to find relevant nodes:
- `comfyui_nodes` with filter "sampler" → KSampler, KSamplerAdvanced, etc.
- `comfyui_nodes` with filter "loader" → UNETLoader, CLIPLoader, LoraLoader, etc.
- `comfyui_nodes` with filter "controlnet" → ControlNet nodes

### Step 2: Build the Graph
Common workflow patterns:

**Basic txt2img pipeline:**
```
UNETLoader → KSampler
CLIPLoader → CLIPTextEncode → KSampler (positive)
CLIPTextEncode → ConditioningZeroOut → KSampler (negative)
EmptySD3LatentImage → KSampler
KSampler → VAEDecode → SaveImage
VAELoader → VAEDecode
```

**With LoRA:**
```
UNETLoader → LoraLoaderModelOnly → KSampler
```

**With ControlNet:**
```
ControlNetLoader → ControlNetApply
CLIPTextEncode → ControlNetApply → KSampler (positive)
LoadImage → ControlNetApply (image input)
```

**Image-to-image (img2img):**
```
LoadImage → VAEEncode → KSampler (latent_image, denoise < 1.0)
```

### Step 3: Submit
Use `comfyui_queue_workflow` to submit the raw workflow JSON.
Then use `comfyui_get_result` to poll for completion and get output images.

## Common Node Types

### Model Loading
| Node | Inputs | Outputs | Notes |
|------|--------|---------|-------|
| UNETLoader | unet_name, weight_dtype | MODEL | Main diffusion model |
| CLIPLoader | clip_name, type, device | CLIP | Single text encoder |
| DualCLIPLoader | clip_name1, clip_name2, type | CLIP | For Flux 1 (clip_l + t5xxl) |
| VAELoader | vae_name | VAE | VAE decoder/encoder |
| LoraLoaderModelOnly | model, lora_name, strength | MODEL | LoRA on model only |
| LoraLoader | model, clip, lora_name, strength_model, strength_clip | MODEL, CLIP | LoRA on model + clip |
| ControlNetLoader | control_net_name | CONTROL_NET | ControlNet model |
| UpscaleModelLoader | model_name | UPSCALE_MODEL | ESRGAN etc. |

### Text Encoding
| Node | Inputs | Outputs | Notes |
|------|--------|---------|-------|
| CLIPTextEncode | clip, text | CONDITIONING | Standard text encoding |
| CLIPTextEncodeFlux | clip, clip_l, t5xxl, guidance | CONDITIONING | Flux 1 with dual prompts |
| ConditioningZeroOut | conditioning | CONDITIONING | Empty/negative conditioning |

### Sampling
| Node | Inputs | Outputs | Notes |
|------|--------|---------|-------|
| KSampler | model, positive, negative, latent_image, seed, steps, cfg, sampler_name, scheduler, denoise | LATENT | Main sampler |
| KSamplerAdvanced | model, positive, negative, latent_image, add_noise, noise_seed, steps, cfg, sampler_name, scheduler, start_at_step, end_at_step, return_with_leftover_noise | LATENT | Advanced control |

### Image Operations
| Node | Inputs | Outputs | Notes |
|------|--------|---------|-------|
| LoadImage | image (filename) | IMAGE, MASK | Load from ComfyUI input/ |
| SaveImage | images, filename_prefix | - | Save to output/ |
| PreviewImage | images | - | Temp preview |
| VAEDecode | samples, vae | IMAGE | Latent → image |
| VAEEncode | pixels, vae | LATENT | Image → latent |
| ImageUpscaleWithModel | upscale_model, image | IMAGE | AI upscale |
| ImageScaleBy | image, upscale_method, scale_by | IMAGE | Simple resize |

### Latent
| Node | Inputs | Outputs | Notes |
|------|--------|---------|-------|
| EmptyLatentImage | width, height, batch_size | LATENT | For SD 1.5/SDXL |
| EmptySD3LatentImage | width, height, batch_size | LATENT | For SD3/Flux/Z-Image-Turbo |

### Model Modifications
| Node | Inputs | Outputs | Notes |
|------|--------|---------|-------|
| ModelSamplingAuraFlow | model, shift | MODEL | Required for Z-Image-Turbo (shift=3) |
| ControlNetApplyAdvanced | positive, negative, control_net, image, strength, start_percent, end_percent | CONDITIONING, CONDITIONING | Apply ControlNet |

## Model-Specific Node Requirements

**Z-Image-Turbo**: CLIPLoader(type="lumina2") + ModelSamplingAuraFlow(shift=3)
**Flux 1 Dev**: DualCLIPLoader(type="flux") + CLIPTextEncodeFlux
**Flux 2 Dev**: CLIPLoader(type="flux2") + CLIPTextEncode

## Tips

- Always include a SaveImage node for output capture
- Use string node IDs for clarity (e.g., "model_loader", "sampler")
- Test with `comfyui_queue_workflow`, check results with `comfyui_get_result`
- If a node is missing, the user may need to install a custom node package
