"""Template loading, parameter substitution, and auto-selection."""

import copy
import json
import os
import random
from pathlib import Path

from models import TemplateInfo


class TemplateManager:
    """Manages ComfyUI API-format workflow templates."""

    def __init__(self, templates_dir: str | None = None):
        if templates_dir is None:
            templates_dir = str(
                Path(__file__).parent.parent / "templates"
            )
        self.templates_dir = templates_dir
        self._templates: dict[str, TemplateInfo] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Scan templates directory and load all JSON templates."""
        templates_path = Path(self.templates_dir)
        if not templates_path.exists():
            return

        for json_file in templates_path.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                meta = data.get("_meta")
                if not meta:
                    continue

                # Separate workflow from metadata
                workflow = {k: v for k, v in data.items() if k != "_meta"}

                info = TemplateInfo(
                    name=meta["name"],
                    description=meta.get("description", ""),
                    category=meta.get("category", ""),
                    parameters=meta.get("parameters", {}),
                    models=meta.get("models", {}),
                    workflow=workflow,
                )
                self._templates[info.name] = info
            except (json.JSONDecodeError, KeyError) as e:
                # Skip malformed templates
                continue

    def list_templates(self) -> list[dict]:
        """Return list of available templates with their metadata."""
        result = []
        for info in self._templates.values():
            params_summary = {}
            for pname, pconfig in info.parameters.items():
                params_summary[pname] = {
                    "default": pconfig.get("default"),
                    "description": pconfig.get("description", ""),
                }
            result.append({
                "name": info.name,
                "description": info.description,
                "category": info.category,
                "parameters": params_summary,
                "models": info.models,
            })
        return result

    def get_template(self, name: str) -> TemplateInfo | None:
        """Get a template by name."""
        return self._templates.get(name)

    def fill_template(self, name: str, params: dict) -> dict:
        """
        Load a template and substitute parameters.

        The _meta.parameters map tells us which node/field to set:
          "prompt": {"node": "27", "field": "inputs.text"}

        Returns the workflow dict ready for POST /prompt.
        """
        info = self._templates.get(name)
        if not info:
            raise ValueError(f"Template '{name}' not found. Available: {list(self._templates.keys())}")

        workflow = copy.deepcopy(info.workflow)

        # For Flux 1: if prompt_t5 is a parameter but not provided,
        # copy the main prompt to it so both encoders get the same text
        if "prompt_t5" in info.parameters and "prompt_t5" not in params:
            if "prompt" in params:
                params = dict(params)  # avoid mutating caller's dict
                params["prompt_t5"] = params["prompt"]

        for param_name, param_config in info.parameters.items():
            # Get the value: use provided param, or template default
            if param_name in params and params[param_name] is not None:
                value = params[param_name]
                # Skip sentinel values (-1 means "use default")
                if isinstance(value, (int, float)) and value == -1:
                    continue
            else:
                continue  # No value provided, keep template default

            # Special handling for seed: -1 or 0 means random
            if param_name == "seed" and value in (-1, 0):
                value = random.randint(1, 2**32 - 1)

            # Navigate to the target field and set it
            node_id = str(param_config["node"])
            field_path = param_config["field"]  # e.g., "inputs.text"

            if node_id not in workflow:
                continue

            # Walk the field path
            parts = field_path.split(".")
            target = workflow[node_id]
            for part in parts[:-1]:
                if isinstance(target, dict) and part in target:
                    target = target[part]
                else:
                    break
            else:
                target[parts[-1]] = value

        return workflow

    def auto_select(
        self,
        has_input_image: bool = False,
        quality: str = "balanced",
    ) -> str | None:
        """
        Auto-select the best template based on the task.

        Args:
            has_input_image: True if user provided an input image
            quality: "fast", "balanced", or "quality"

        Returns:
            Template name, or None if no suitable template found.
        """
        if has_input_image:
            # Look for img2img or edit templates
            for name in ["img_edit_flux2_klein", "img2img"]:
                if name in self._templates:
                    return name

        # Text-to-image selection based on quality preference
        if quality == "fast":
            preference = ["txt2img_z_image_turbo"]
        elif quality == "quality":
            preference = ["txt2img_flux2_dev", "txt2img_flux1_dev", "txt2img_z_image_turbo"]
        else:  # balanced
            preference = ["txt2img_z_image_turbo", "txt2img_flux1_dev", "txt2img_flux2_dev"]

        for name in preference:
            if name in self._templates:
                return name

        # Fallback: return first available template
        if self._templates:
            return next(iter(self._templates))
        return None
