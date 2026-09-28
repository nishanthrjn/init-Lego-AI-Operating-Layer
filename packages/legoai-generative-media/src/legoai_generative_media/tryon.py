"""TemplateKind.TRY_ON: the approved Qwen-Image-Edit-2509 try-on graph.

An original API-format graph built only from built-in ComfyUI nodes. It was
checked against ComfyUI 0.37 node sources and the bundled 2509 template as
evidence, not copied. Only three slots change per invocation:

- the person upload name (node 6);
- the garment upload name (node 7);
- the seed (node 13).

Model filenames are operator profile values fixed in the approved bytes.
The edit instruction, sampler, geometry and output node are fixed.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .values import ApprovedWorkflowRef, UploadedImageRef
from .workflow import (
    MAX_WORKFLOW_BYTES,
    OUTPUT_NODE,
    ModelRequirement,
    TemplateKind,
    basename,
    json_object,
)

TEMPLATE_ID = "qwen-image-edit-2509"
# Fixed portrait output. 768 and 1024 are multiples of 16 (VAE x8, patch x2),
# about 0.79 MP, close to the model's ~1 MP working area, and within the
# package's 1024 px output ceiling.
WIDTH, HEIGHT = 768, 1024
INSTRUCTION = (
    "Dress the person in the garment shown in the second reference image. "
    "Preserve the person's identity, pose and scene while replacing only the "
    "clothing as naturally as possible."
)
_INPUT = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\.png)"
    r" \[temp\]"
)


@dataclass(frozen=True, slots=True)
class TryOnModels:
    """Operator-installed Qwen-Image-Edit-2509 components (basenames only)."""

    diffusion_model: str
    text_encoder: str
    vae: str

    def __post_init__(self) -> None:
        basename(self.diffusion_model, "diffusion model")
        basename(self.text_encoder, "text encoder")
        basename(self.vae, "vae")


def tryon_template(models: TryOnModels) -> dict[str, Any]:
    """The approved graph with empty input slots and seed 0."""
    if type(models) is not TryOnModels:
        raise TypeError("TryOnModels required")
    encoder = {
        "clip": ["2", 0],
        "vae": ["3", 0],
        "image1": ["8", 0],  # Scaled person.
        "image2": ["7", 0],  # Garment; the encoder rescales references itself.
    }
    return {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": models.diffusion_model, "weight_dtype": "default"},
        },
        "2": {
            "class_type": "CLIPLoader",
            "inputs": {"clip_name": models.text_encoder, "type": "qwen_image"},
        },
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": models.vae}},
        "4": {
            "class_type": "ModelSamplingAuraFlow",
            "inputs": {"model": ["1", 0], "shift": 3.0},
        },
        "5": {"class_type": "CFGNorm", "inputs": {"model": ["4", 0], "strength": 1.0}},
        "6": {"class_type": "LoadImage", "inputs": {"image": ""}},
        "7": {"class_type": "LoadImage", "inputs": {"image": ""}},
        # Aspect-preserving centre crop, then resize: no distortion, no padding.
        "8": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["6", 0],
                "upscale_method": "lanczos",
                "width": WIDTH,
                "height": HEIGHT,
                "crop": "center",
            },
        },
        OUTPUT_NODE: {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "legoai_tryon", "images": ["14", 0]},
        },
        "10": {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["8", 0], "vae": ["3", 0]},
        },
        "11": {
            "class_type": "TextEncodeQwenImageEditPlus",
            "inputs": {**encoder, "prompt": INSTRUCTION},
        },
        "12": {
            "class_type": "TextEncodeQwenImageEditPlus",
            "inputs": {**encoder, "prompt": ""},
        },
        "13": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,
                "steps": 20,
                "cfg": 4.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
                "model": ["5", 0],
                "positive": ["11", 0],
                "negative": ["12", 0],
                "latent_image": ["10", 0],
            },
        },
        "14": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["13", 0], "vae": ["3", 0]},
        },
    }


def _same(a: object, b: object) -> bool:
    # Serialized comparison also rejects bool-for-number substitutions.
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


@dataclass(frozen=True, slots=True)
class TryOnAttribution:
    seed: int
    person: UploadedImageRef
    garment: UploadedImageRef


@dataclass(frozen=True, slots=True)
class ApprovedTryOnWorkflow:
    reference: ApprovedWorkflowRef
    models: TryOnModels = field(repr=False)
    content: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.reference) is not ApprovedWorkflowRef
            or type(self.models) is not TryOnModels
            or type(self.content) is not bytes
        ):
            raise TypeError("workflow values required")
        if len(self.content) > MAX_WORKFLOW_BYTES:
            raise ValueError("workflow oversized")
        if hashlib.sha256(self.content).hexdigest() != self.reference.sha256:
            raise ValueError("workflow digest mismatch")
        if not _same(json_object(self.content), tryon_template(self.models)):
            raise ValueError("unknown workflow shape")

    @classmethod
    def load(
        cls, path: Path, reference: ApprovedWorkflowRef, models: TryOnModels
    ) -> ApprovedTryOnWorkflow:
        with path.open("rb") as source:
            content = source.read(MAX_WORKFLOW_BYTES + 1)
        return cls(reference, models, content)

    @property
    def kind(self) -> TemplateKind:
        return TemplateKind.TRY_ON

    @property
    def required_nodes(self) -> frozenset[str]:
        return frozenset(v["class_type"] for v in tryon_template(self.models).values())

    @property
    def required_models(self) -> tuple[ModelRequirement, ...]:
        return (
            ("UNETLoader", "unet_name", self.models.diffusion_model),
            ("CLIPLoader", "clip_name", self.models.text_encoder),
            ("VAELoader", "vae_name", self.models.vae),
        )

    @property
    def geometry(self) -> tuple[int, int]:
        return (WIDTH, HEIGHT)

    def graph(
        self, person: UploadedImageRef, garment: UploadedImageRef, seed: int | None
    ) -> dict[str, Any]:
        """Patch exactly the three mutable slots of the approved bytes."""
        if (
            type(person) is not UploadedImageRef
            or type(garment) is not UploadedImageRef
        ):
            raise TypeError("uploaded references required")
        if person.provider_name == garment.provider_name:
            raise ValueError("person and garment must be distinct uploads")
        value = 0 if seed is None else seed
        if type(value) is not int or not 0 <= value <= 2**63 - 1:
            raise ValueError("seed must be integer in 0..2**63-1")
        graph = json_object(self.content)
        graph["6"]["inputs"]["image"] = f"{person.provider_name} [{person.storage}]"
        graph["7"]["inputs"]["image"] = f"{garment.provider_name} [{garment.storage}]"
        graph["13"]["inputs"]["seed"] = value
        if len(json.dumps({"prompt": graph}, ensure_ascii=True)) > MAX_WORKFLOW_BYTES:
            raise ValueError("request oversized")
        return graph

    def attribute(self, graph: object) -> TryOnAttribution:
        """Recover seed and input locators if graph is exactly this template."""
        try:
            person = graph["6"]["inputs"]["image"]  # type: ignore[index]
            garment = graph["7"]["inputs"]["image"]  # type: ignore[index]
            seed = graph["13"]["inputs"]["seed"]  # type: ignore[index]
        except KeyError, TypeError, IndexError:
            raise ValueError("graph not attributable") from None
        refs = []
        for value in (person, garment):
            match = _INPUT.fullmatch(value) if type(value) is str else None
            if match is None:
                raise ValueError("input slot is not a generated temp upload")
            refs.append(UploadedImageRef(match.group(1)))
        if type(seed) is not int:
            raise ValueError("graph not attributable")
        if not _same(graph, self.graph(refs[0], refs[1], seed)):
            raise ValueError("graph not attributable to approved workflow")
        return TryOnAttribution(seed, refs[0], refs[1])

    def seed_of(self, graph: object) -> int:
        return self.attribute(graph).seed
