"""One fixed API workflow shape, not a graph DSL or arbitrary graph executor."""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .values import ApprovedWorkflowRef, TextToImageRequest

MAX_WORKFLOW_BYTES = 256 * 1024


def template(checkpoint: str) -> dict[str, Any]:
    if type(checkpoint) is not str or not checkpoint or len(checkpoint) > 128:
        raise ValueError("checkpoint basename required")
    if any(c in checkpoint for c in "/\\:") or checkpoint in (".", ".."):
        raise ValueError("checkpoint path forbidden")
    if any(ord(c) < 32 or ord(c) == 127 for c in checkpoint):
        raise ValueError("checkpoint controls forbidden")
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,
                "steps": 20,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 512, "height": 512, "batch_size": 1},
        },
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["4", 1]}},
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "legoai", "images": ["8", 0]},
        },
    }


def json_object(data: bytes) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    value = json.loads(data, object_pairs_hook=pairs)
    if type(value) is not dict:
        raise ValueError("JSON object required")
    return value


@dataclass(frozen=True, slots=True)
class ApprovedWorkflow:
    reference: ApprovedWorkflowRef
    checkpoint: str = field(repr=False)
    content: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.reference) is not ApprovedWorkflowRef
            or type(self.content) is not bytes
        ):
            raise TypeError("workflow values required")
        if len(self.content) > MAX_WORKFLOW_BYTES:
            raise ValueError("workflow oversized")
        if hashlib.sha256(self.content).hexdigest() != self.reference.sha256:
            raise ValueError("workflow digest mismatch")
        expected = template(self.checkpoint)
        actual = json_object(self.content)
        # Serialized comparison also rejects bool-for-number substitutions.
        if json.dumps(actual, sort_keys=True) != json.dumps(expected, sort_keys=True):
            raise ValueError("unknown workflow shape")

    @classmethod
    def load(
        cls, path: Path, reference: ApprovedWorkflowRef, checkpoint: str
    ) -> ApprovedWorkflow:
        with path.open("rb") as source:
            content = source.read(MAX_WORKFLOW_BYTES + 1)
        return cls(reference, checkpoint, content)

    def bind(self, request: TextToImageRequest) -> bytes:
        graph = json_object(self.content)
        graph["6"]["inputs"]["text"] = request.prompt
        graph["3"]["inputs"]["seed"] = request.seed if request.seed is not None else 0
        output = json.dumps({"prompt": graph}, ensure_ascii=True).encode("utf-8")
        if len(output) > MAX_WORKFLOW_BYTES:
            raise ValueError("request oversized")
        return output

    def attribute(self, graph: object) -> TextToImageRequest:
        """Recover the request whose binding reproduces graph exactly, or reject.

        Proves shape equivalence with this approved workflow only; it is not a
        cryptographic link to who submitted the graph or when.
        """
        try:
            text = graph["6"]["inputs"]["text"]  # type: ignore[index]
            seed = graph["3"]["inputs"]["seed"]  # type: ignore[index]
        except KeyError, TypeError, IndexError:
            raise ValueError("graph not attributable") from None
        request = TextToImageRequest(text, seed)
        expected = json_object(self.bind(request))["prompt"]
        if json.dumps(graph, sort_keys=True) != json.dumps(expected, sort_keys=True):
            raise ValueError("graph not attributable to approved workflow")
        return request
