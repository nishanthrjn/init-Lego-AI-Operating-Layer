"""TemplateKind.TRY_ON: exact shape, digest pinning, three mutable slots only."""

import hashlib
import json
from typing import Any

import pytest
from media_support import (
    GARMENT_REF,
    PERSON_REF,
    TRYON_MODELS,
    tryon_graph,
    tryon_workflow,
    workflow,
)

from legoai_generative_media.tryon import (
    HEIGHT,
    INSTRUCTION,
    WIDTH,
    ApprovedTryOnWorkflow,
    TryOnModels,
    tryon_template,
)
from legoai_generative_media.values import (
    ApprovedWorkflowRef,
    TextToImageRequest,
    UploadedImageRef,
)
from legoai_generative_media.workflow import TemplateKind

CLASSES = {
    "1": "UNETLoader",
    "2": "CLIPLoader",
    "3": "VAELoader",
    "4": "ModelSamplingAuraFlow",
    "5": "CFGNorm",
    "6": "LoadImage",
    "7": "LoadImage",
    "8": "ImageScale",
    "9": "SaveImage",
    "10": "VAEEncode",
    "11": "TextEncodeQwenImageEditPlus",
    "12": "TextEncodeQwenImageEditPlus",
    "13": "KSampler",
    "14": "VAEDecode",
}


def approve(
    graph: dict[str, Any], models: TryOnModels = TRYON_MODELS
) -> ApprovedTryOnWorkflow:
    content = json.dumps(graph).encode()
    ref = ApprovedWorkflowRef("tryon", "1", hashlib.sha256(content).hexdigest())
    return ApprovedTryOnWorkflow(ref, models, content)


def test_exact_graph_shape_and_fixed_parameters() -> None:
    graph = tryon_template(TRYON_MODELS)
    assert {k: v["class_type"] for k, v in graph.items()} == CLASSES
    assert graph["4"]["inputs"]["shift"] == 3.0
    assert graph["5"]["inputs"]["strength"] == 1.0
    sampler = graph["13"]["inputs"]
    assert (sampler["steps"], sampler["cfg"], sampler["denoise"]) == (20, 4.0, 1.0)
    assert (sampler["sampler_name"], sampler["scheduler"]) == ("euler", "simple")
    scale = graph["8"]["inputs"]
    assert (scale["width"], scale["height"], scale["crop"]) == (WIDTH, HEIGHT, "center")
    assert (WIDTH, HEIGHT) == (768, 1024) and WIDTH % 16 == HEIGHT % 16 == 0
    assert graph["11"]["inputs"]["prompt"] == INSTRUCTION
    assert graph["12"]["inputs"]["prompt"] == ""
    for encoder in ("11", "12"):  # Negative mirrors the positive references.
        assert graph[encoder]["inputs"]["image1"] == ["8", 0]
        assert graph[encoder]["inputs"]["image2"] == ["7", 0]
    assert graph["10"]["inputs"]["pixels"] == ["8", 0]  # Latent from scaled person.
    assert graph["9"]["inputs"]["images"] == ["14", 0]
    assert "LoraLoaderModelOnly" not in {v["class_type"] for v in graph.values()}


def test_declared_requirements() -> None:
    approved = tryon_workflow()
    assert (
        approved.kind is TemplateKind.TRY_ON
        and workflow().kind is TemplateKind.TEXT_TO_IMAGE
    )
    assert approved.required_nodes == set(CLASSES.values())
    assert approved.required_models == (
        ("UNETLoader", "unet_name", TRYON_MODELS.diffusion_model),
        ("CLIPLoader", "clip_name", TRYON_MODELS.text_encoder),
        ("VAELoader", "vae_name", TRYON_MODELS.vae),
    )
    assert approved.geometry == (768, 1024) and workflow().geometry == (512, 512)


def mutate(change: str) -> dict[str, Any]:
    graph = tryon_template(TRYON_MODELS)
    if change == "unexpected node":
        graph["15"] = {"class_type": "LoraLoaderModelOnly", "inputs": {}}
    elif change == "missing node":
        del graph["12"]
    elif change == "wrong class":
        graph["8"]["class_type"] = "FluxKontextImageScale"
    elif change == "instruction":
        graph["11"]["inputs"]["prompt"] = "Make it red."
    elif change == "steps":
        graph["13"]["inputs"]["steps"] = 4
    elif change == "geometry":
        graph["8"]["inputs"]["width"] = 832
    elif change == "extra field":
        graph["9"]["inputs"]["subfolder"] = "x"
    elif change == "bool for number":
        graph["13"]["inputs"]["denoise"] = True
    return graph


@pytest.mark.parametrize(
    "change",
    [
        "unexpected node",
        "missing node",
        "wrong class",
        "instruction",
        "steps",
        "geometry",
        "extra field",
        "bool for number",
    ],
)
def test_only_the_exact_template_is_approvable(change: str) -> None:
    with pytest.raises(ValueError):
        approve(mutate(change))


def test_digest_pinning_and_model_binding() -> None:
    approved = tryon_workflow()
    with pytest.raises(ValueError):
        ApprovedTryOnWorkflow(approved.reference, TRYON_MODELS, approved.content + b" ")
    other = TryOnModels(
        "qwen_image_edit_2509_bf16.safetensors",
        TRYON_MODELS.text_encoder,
        TRYON_MODELS.vae,
    )
    with pytest.raises(ValueError):  # Bytes approved for other model files.
        ApprovedTryOnWorkflow(approved.reference, other, approved.content)
    assert approve(tryon_template(other), other).models == other  # Re-approval path.
    for bad in ("../x.safetensors", "C:model", "a/b", ""):
        with pytest.raises(ValueError):
            TryOnModels(bad, "t", "v")


def test_binding_changes_only_three_slots() -> None:
    base = tryon_template(TRYON_MODELS)
    bound = tryon_graph(123)
    changed = {
        (node, key)
        for node in base
        for key in base[node]["inputs"]
        if base[node]["inputs"][key] != bound[node]["inputs"][key]
    }
    assert changed == {("6", "image"), ("7", "image"), ("13", "seed")}
    assert bound["6"]["inputs"]["image"] == f"{PERSON_REF.provider_name} [temp]"
    assert bound["7"]["inputs"]["image"] == f"{GARMENT_REF.provider_name} [temp]"
    assert bound["13"]["inputs"]["seed"] == 123
    assert tryon_graph(None)["13"]["inputs"]["seed"] == 0


def test_binding_rejects_invalid_slots() -> None:
    approved = tryon_workflow()
    with pytest.raises(ValueError):
        approved.graph(PERSON_REF, PERSON_REF, 1)
    for seed in (-1, 2**63, True):
        with pytest.raises(ValueError):
            approved.graph(PERSON_REF, GARMENT_REF, seed)
    with pytest.raises(TypeError):
        approved.graph("x.png", GARMENT_REF, 1)  # type: ignore[arg-type]


def test_attribution_recovers_seed_and_locators() -> None:
    attribution = tryon_workflow().attribute(tryon_graph(99))
    assert attribution.seed == 99
    assert (attribution.person, attribution.garment) == (PERSON_REF, GARMENT_REF)
    assert tryon_workflow().seed_of(tryon_graph(5)) == 5


def drifted(change: str) -> Any:
    graph = tryon_graph(7)
    if change == "user filename":
        graph["6"]["inputs"]["image"] = "holiday photo.png [temp]"
    elif change == "not temp":
        graph["6"]["inputs"]["image"] = f"{PERSON_REF.provider_name} [input]"
    elif change == "traversal":
        graph["7"]["inputs"]["image"] = (
            "../11111111-1111-4111-8111-111111111111.png [temp]"
        )
    elif change == "same input twice":
        graph["7"]["inputs"]["image"] = graph["6"]["inputs"]["image"]
    elif change == "model":
        graph["1"]["inputs"]["unet_name"] = "other.safetensors"
    elif change == "instruction":
        graph["11"]["inputs"]["prompt"] = "Remove the person."
    elif change == "geometry":
        graph["8"]["inputs"]["height"] = 768
    elif change == "output node":
        graph["9"]["inputs"]["filename_prefix"] = "elsewhere"
    elif change == "text-to-image graph":
        return workflow().graph(TextToImageRequest("x", 7))
    return graph


@pytest.mark.parametrize(
    "change",
    [
        "user filename",
        "not temp",
        "traversal",
        "same input twice",
        "model",
        "instruction",
        "geometry",
        "output node",
        "text-to-image graph",
    ],
)
def test_attribution_rejects_drift(change: str) -> None:
    with pytest.raises(ValueError):
        tryon_workflow().attribute(drifted(change))


def test_uploaded_ref_is_the_only_input_locator() -> None:
    with pytest.raises(ValueError):
        UploadedImageRef("person.png")
