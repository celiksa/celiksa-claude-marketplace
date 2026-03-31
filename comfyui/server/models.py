from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GenerateParams:
    prompt: str
    template: str = "auto"
    width: int = 1024
    height: int = 1024
    seed: int = -1  # -1 = random
    steps: int = -1  # -1 = use template default
    cfg: float = -1  # -1 = use template default
    negative_prompt: str = ""
    input_image_path: str = ""
    denoise: float = -1


@dataclass
class ImageResult:
    filename: str
    subfolder: str
    folder_type: str  # "output" or "temp"
    path: str  # full local path
    url: str  # ComfyUI view URL


@dataclass
class GenerateResult:
    prompt_id: str
    images: list[ImageResult] = field(default_factory=list)
    template_used: str = ""
    elapsed_seconds: float = 0.0
    seed_used: int = 0


@dataclass
class TemplateInfo:
    name: str
    description: str
    category: str
    parameters: dict  # param_name -> {node, field, default}
    models: dict  # model_type -> filename
    workflow: dict  # API-format workflow (without _meta)
