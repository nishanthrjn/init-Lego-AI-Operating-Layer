"""ADR-002: F0/F1 import policy, including type-only imports and re-exports.

This small source checker is a development control, not hostile-code isolation.
Synthetic graphs are parsed as text, never written to executable import paths.
"""

import ast
import sys
from pathlib import Path

import pytest


def violations(sources: dict[str, str]) -> set[str]:
    errors: set[str] = set()
    edges: dict[str, set[str]] = {name: set() for name in sources}
    for name, source in sources.items():
        tree = ast.parse(source)
        package = name.removesuffix(".__init__")
        if name.endswith(".__init__"):
            if any(
                not (
                    isinstance(n, ast.Expr)
                    and isinstance(n.value, ast.Constant)
                    and isinstance(n.value.value, str)
                )
                for n in tree.body
            ):
                errors.add("initializer")
        else:
            package = name.rpartition(".")[0]
        for node in ast.walk(tree):
            targets: list[str] = []
            if isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if any(alias.name == "*" for alias in node.names):
                    errors.add("star")
                base = node.module or ""
                if node.level:
                    parts = package.split(".")
                    if node.level > len(parts):
                        errors.add("relative-escape")
                        continue
                    base = ".".join(
                        parts[: len(parts) - node.level + 1] + ([base] if base else [])
                    )
                targets = [base] + [f"{base}.{a.name}" for a in node.names]
            elif isinstance(node, (ast.Name, ast.Attribute)):
                identifier = node.id if isinstance(node, ast.Name) else node.attr
                if identifier in {
                    "__import__",
                    "eval",
                    "exec",
                    "compile",
                }:
                    errors.add("dynamic")
            for target in targets:
                root = target.split(".")[0]
                if root in {"importlib", "runpy", "pkgutil", "ctypes"} or target.rsplit(
                    ".", 1
                )[-1] in {"__import__", "eval", "exec", "compile"}:
                    errors.add("dynamic")
                if root in {"tests", "test_support"}:
                    errors.add("test-import")
                elif root == "legoai":
                    if name.startswith("legoai.application.") and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.application"
                        or target.startswith("legoai.application.")
                        # ADR-002 SS9.2: Application's allowed-foreign-targets row
                        # includes G (Governance) and O (Evidence/Observability).
                        # F4 is the first real consumer of both; only these two
                        # are widened here, not the full ADR-002 maximum.
                        or target == "legoai.governance"
                        or target.startswith("legoai.governance.")
                        or target == "legoai.evidence"
                        or target.startswith("legoai.evidence.")
                    ):
                        errors.add("application-owner")
                    if name.startswith("legoai.application.") and any(
                        target == f"legoai.application.{layer}"
                        or target.startswith(f"legoai.application.{layer}.")
                        for layer in ("ports", "reference", "runtime")
                    ):
                        errors.add("values-layer")
                    if name.startswith("legoai.reference.application.") and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.application.values"
                        or target.startswith("legoai.application.values.")
                        or target == "legoai.reference.application"
                        or target.startswith("legoai.reference.application.")
                        # ADR-002 SS9.2/SS7: a reference realization gets the
                        # same allowed-peer permissions as its owner's row --
                        # F5's codec constructs Principal/EvidenceRequirement
                        # instances, mirroring application-owner's own F4
                        # widening to G (governance) and O (evidence) above.
                        or target == "legoai.governance.values"
                        or target.startswith("legoai.governance.values.")
                        or target == "legoai.evidence.values"
                        or target.startswith("legoai.evidence.values.")
                        # ADR-002 SS7: "Adapter implementation" is its own
                        # permission row (K and its implemented Port). Only
                        # the actual Port realization module(s) -- named by
                        # the "_store" suffix convention -- may import the
                        # Port they implement; F5's codec (representation
                        # only, no realization) deliberately still cannot.
                        or (
                            name.endswith("_store")
                            and (
                                target == "legoai.application.ports"
                                or target.startswith("legoai.application.ports.")
                            )
                        )
                    ):
                        errors.add("reference-owner")
                    if name.startswith("legoai.kernel.") and not (
                        target == "legoai.kernel" or target.startswith("legoai.kernel.")
                    ):
                        errors.add("kernel-owner")
                    if name.startswith("legoai.governance.") and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.governance"
                        or target.startswith("legoai.governance.")
                    ):
                        errors.add("governance-owner")
                    if name.startswith("legoai.governance.") and any(
                        target == f"legoai.governance.{layer}"
                        or target.startswith(f"legoai.governance.{layer}.")
                        for layer in ("ports", "reference", "runtime")
                    ):
                        errors.add("values-layer")
                    if name == "legoai.evidence.values" and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.evidence.values"
                        or target.startswith("legoai.evidence.values.")
                    ):
                        # F4 gives evidence.values only Kernel, deliberately
                        # stricter than ADR-002's G-inclusive maximum for O,
                        # matching the Gate-1 plan's own narrower F4 scope.
                        errors.add("evidence-owner")
                    if name == "legoai.evidence.ports" and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.evidence.values"
                        or target.startswith("legoai.evidence.values.")
                        # ADR-002 SS9.2: O-row's allowed-foreign row includes
                        # G (Governance); Gate-2 M8 is the first real
                        # consumer (evidence attributable to a Principal
                        # issuer and, per the M6 capabilities.ports ->
                        # plugins.ports precedent, to a foreign owner's
                        # Port-level operation-result value).
                        or target == "legoai.governance.values"
                        or target.startswith("legoai.governance.values.")
                        or target == "legoai.governance.ports"
                        or target.startswith("legoai.governance.ports.")
                    ):
                        errors.add("evidence-owner")
                    if name.startswith("legoai.evidence.") and any(
                        target == f"legoai.evidence.{layer}"
                        or target.startswith(f"legoai.evidence.{layer}.")
                        for layer in ("ports", "reference", "runtime")
                    ):
                        errors.add("values-layer")
                    if name.startswith("legoai.observability.") and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.observability"
                        or target.startswith("legoai.observability.")
                    ):
                        # F8a gives observability only Kernel, narrower than
                        # ADR-002 SS9.2's G-inclusive maximum for O -- no
                        # actual field in this batch needs Governance.
                        errors.add("observability-owner")
                    if name.startswith("legoai.observability.") and any(
                        target == f"legoai.observability.{layer}"
                        or target.startswith(f"legoai.observability.{layer}.")
                        for layer in ("ports", "reference", "runtime")
                    ):
                        errors.add("values-layer")
                    if name == "legoai.reference.observation" and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.observability.values"
                        or target.startswith("legoai.observability.values.")
                        or target == "legoai.observability.ports"
                        or target.startswith("legoai.observability.ports.")
                    ):
                        errors.add("reference-owner")
                    if name == "legoai.reference.governance" and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.governance.values"
                        or target.startswith("legoai.governance.values.")
                        or target == "legoai.governance.ports"
                        or target.startswith("legoai.governance.ports.")
                    ):
                        # Gate-2 M4's reference realization gets the same
                        # allowed-peer permissions as its owner's row
                        # (ADR-002 SS9.2/SS7) -- its own Port/values only,
                        # never other reference realizations or runtime.
                        errors.add("reference-owner")
                    if name == "legoai.capabilities.values" and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.capabilities.values"
                        or target.startswith("legoai.capabilities.values.")
                    ):
                        # F7 gives capabilities.values only Kernel, narrower
                        # than ADR-002 SS9.2's G/R/O/X maximum for the C
                        # plane -- no field in that batch needs any peer.
                        errors.add("capabilities-owner")
                    if name == "legoai.capabilities.ports" and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.capabilities.values"
                        or target.startswith("legoai.capabilities.values.")
                        # ADR-002 SS9.2: Capabilities' (C) allowed-foreign
                        # row includes X (Plugins); Gate-2 M6 is the first
                        # real consumer, only this one peer is widened, and
                        # only for ports.py (operation request/result
                        # definitions may embed a foreign owner's value).
                        or target == "legoai.plugins.values"
                        or target.startswith("legoai.plugins.values.")
                        or target == "legoai.plugins.ports"
                        or target.startswith("legoai.plugins.ports.")
                    ):
                        errors.add("capabilities-owner")
                    if name.startswith("legoai.capabilities.") and any(
                        target == f"legoai.capabilities.{layer}"
                        or target.startswith(f"legoai.capabilities.{layer}.")
                        for layer in ("ports", "reference", "runtime")
                    ):
                        errors.add("values-layer")
                    if name == "legoai.execution.values" and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.execution.values"
                        or target.startswith("legoai.execution.values.")
                    ):
                        # Gate-2 M1 gives execution.values only Kernel: no
                        # field in this batch needs Governance/Capabilities/
                        # Resources/Plugins (ADR-002 SS9.2's E-row maximum
                        # includes those peers, but none is a canonically
                        # justified M1 field -- see the Gate-2 plan SS14/21).
                        errors.add("execution-owner")
                    if name == "legoai.execution.ports" and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.execution.values"
                        or target.startswith("legoai.execution.values.")
                        # ADR-002 SS9.2's E-row maximum includes G, C, O, X;
                        # Gate-2 M9 is the first real consumer of Governance
                        # (Authorization/SecurityContext), Capabilities
                        # (Catalog) and Evidence (custody) Port-level values.
                        or target == "legoai.governance.values"
                        or target.startswith("legoai.governance.values.")
                        or target == "legoai.governance.ports"
                        or target.startswith("legoai.governance.ports.")
                        or target == "legoai.capabilities.values"
                        or target.startswith("legoai.capabilities.values.")
                        or target == "legoai.capabilities.ports"
                        or target.startswith("legoai.capabilities.ports.")
                        or target == "legoai.evidence.values"
                        or target.startswith("legoai.evidence.values.")
                        or target == "legoai.evidence.ports"
                        or target.startswith("legoai.evidence.ports.")
                    ):
                        errors.add("execution-owner")
                    if name.startswith("legoai.execution.") and any(
                        target == f"legoai.execution.{layer}"
                        or target.startswith(f"legoai.execution.{layer}.")
                        for layer in ("ports", "reference", "runtime")
                    ):
                        errors.add("values-layer")
                    if name.startswith("legoai.resources.") and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.resources"
                        or target.startswith("legoai.resources.")
                    ):
                        # Gate-2 M3 gives resources.values only Kernel: no
                        # field needs Governance/Execution/Observability
                        # (ADR-002 SS9.2's R-row maximum is K, G, O for a
                        # future ports.py; values.py stays Kernel-only, same
                        # discipline as execution.values/governance.values).
                        errors.add("resources-owner")
                    if name.startswith("legoai.resources.") and any(
                        target == f"legoai.resources.{layer}"
                        or target.startswith(f"legoai.resources.{layer}.")
                        for layer in ("ports", "reference", "runtime")
                    ):
                        errors.add("values-layer")
                    if name.startswith("legoai.plugins.") and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.plugins"
                        or target.startswith("legoai.plugins.")
                        # ADR-002 SS9.2: Plugins' (X) allowed-foreign row
                        # includes C (Capabilities); F7 is the first real
                        # consumer, only this one peer is widened.
                        or target == "legoai.capabilities.values"
                        or target.startswith("legoai.capabilities.values.")
                    ):
                        errors.add("plugins-owner")
                    if name.startswith("legoai.plugins.") and any(
                        target == f"legoai.plugins.{layer}"
                        or target.startswith(f"legoai.plugins.{layer}.")
                        for layer in ("ports", "reference", "runtime", "spi")
                    ):
                        errors.add("values-layer")
                    if name == "legoai.reference.plugins" and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.plugins.values"
                        or target.startswith("legoai.plugins.values.")
                        or target == "legoai.plugins.ports"
                        or target.startswith("legoai.plugins.ports.")
                    ):
                        # Gate-2 M5's reference realization gets the same
                        # allowed-peer permissions as its owner's row
                        # (ADR-002 SS9.2/SS7) -- its own Port/values only,
                        # never other reference realizations or runtime.
                        errors.add("reference-owner")
                    if name == "legoai.reference.catalog" and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.capabilities.values"
                        or target.startswith("legoai.capabilities.values.")
                        or target == "legoai.capabilities.ports"
                        or target.startswith("legoai.capabilities.ports.")
                        # ADR-002 SS9.2's C-row maximum includes X (Plugins);
                        # Gate-2 M6's realization is the first real
                        # consumer of Plugin lifecycle/declaration facts.
                        or target == "legoai.plugins.values"
                        or target.startswith("legoai.plugins.values.")
                        or target == "legoai.plugins.ports"
                        or target.startswith("legoai.plugins.ports.")
                    ):
                        errors.add("reference-owner")
                    if name == "legoai.reference.evidence" and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.evidence.values"
                        or target.startswith("legoai.evidence.values.")
                        or target == "legoai.evidence.ports"
                        or target.startswith("legoai.evidence.ports.")
                    ):
                        # Gate-2 M8's reference realization gets the same
                        # allowed-peer permissions as its owner's row
                        # (ADR-002 SS9.2/SS7) -- its own Port/values only,
                        # never other reference realizations or runtime.
                        errors.add("reference-owner")
                    if name == "legoai.reference.execution" and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.execution.values"
                        or target.startswith("legoai.execution.values.")
                        or target == "legoai.execution.ports"
                        or target.startswith("legoai.execution.ports.")
                        or target == "legoai.governance.values"
                        or target.startswith("legoai.governance.values.")
                        or target == "legoai.governance.ports"
                        or target.startswith("legoai.governance.ports.")
                        or target == "legoai.capabilities.values"
                        or target.startswith("legoai.capabilities.values.")
                        or target == "legoai.capabilities.ports"
                        or target.startswith("legoai.capabilities.ports.")
                        or target == "legoai.evidence.values"
                        or target.startswith("legoai.evidence.values.")
                        or target == "legoai.evidence.ports"
                        or target.startswith("legoai.evidence.ports.")
                    ):
                        # Gate-2 M9's reference realization gets the same
                        # allowed-peer permissions as its owner's row
                        # (ADR-002 SS9.2/SS7): it composes the already-
                        # established AuthorizationPort (M4), CatalogPort
                        # (M6) and EvidenceCustodyPort (M8) Ports directly,
                        # never other reference realizations or runtime.
                        errors.add("reference-owner")
                    if name == "legoai.reference.declarations" and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.plugins.values"
                        or target.startswith("legoai.plugins.values.")
                        or target == "legoai.capabilities.values"
                        or target.startswith("legoai.capabilities.values.")
                    ):
                        errors.add("reference-owner")
                    if name == "legoai.reference.resolution" and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.plugins.values"
                        or target.startswith("legoai.plugins.values.")
                        or target == "legoai.capabilities.values"
                        or target.startswith("legoai.capabilities.values.")
                        # ADR-002 line ~176 assigns "Resolution snapshots/
                        # closure/results" to this same module; Gate-2 M7
                        # extends F7's pure compatibility analysis with
                        # runtime resolution over published Catalog state,
                        # so this module (only) also needs the C-row's
                        # Catalog Port operation-result values (never the
                        # `legoai.reference.catalog` realization itself).
                        or target == "legoai.capabilities.ports"
                        or target.startswith("legoai.capabilities.ports.")
                    ):
                        errors.add("reference-owner")
                    if name == "legoai.reference.deterministic" and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.application.values"
                        or target.startswith("legoai.application.values.")
                        or target == "legoai.plugins.values"
                        or target.startswith("legoai.plugins.values.")
                        or target == "legoai.capabilities.values"
                        or target.startswith("legoai.capabilities.values.")
                    ):
                        # The one deterministic fixture describes/executes
                        # its own pure function only -- it must not depend
                        # on the private composition root, SQLite, recovery,
                        # the observation sink realization, or any other
                        # reference-owner realization (F8b task SS42).
                        errors.add("reference-owner")
                    if name == "legoai.intelligence.model.values" and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.intelligence.model.values"
                        or target.startswith("legoai.intelligence.model.values.")
                    ):
                        # v0.1 gives intelligence.model.values only Kernel:
                        # no field in this minimal slice (ModelId/ProviderId/
                        # ChatMessage/ChatRequest/ChatResult/EmbeddingRequest/
                        # EmbeddingResult) needs Governance/Capabilities/
                        # Resources/Plugins, even though ADR-002 SS9.2's I-row
                        # maximum (K, C, M, A, G, R, O, X) would separately
                        # permit those for a future ports.py-level need.
                        errors.add("intelligence-owner")
                    if name == "legoai.intelligence.model.routing" and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.intelligence.model.values"
                        or target.startswith("legoai.intelligence.model.values.")
                    ):
                        errors.add("intelligence-owner")
                    if name == "legoai.reference.model_routing" and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.intelligence.model.routing"
                        or target.startswith("legoai.intelligence.model.routing.")
                    ):
                        errors.add("reference-owner")
                    if name == "legoai.intelligence.model.ports" and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.intelligence.model.values"
                        or target.startswith("legoai.intelligence.model.values.")
                        or target == "legoai.intelligence.model.routing"
                        or target.startswith("legoai.intelligence.model.routing.")
                    ):
                        # ModelPort's two operations and its three effect-
                        # phase exceptions need only this owner's own values
                        # and Kernel -- no Governance/Capabilities dependency
                        # is canonically justified at the Port-contract level
                        # itself (SS9.2's I-row maximum excludes E/Execution
                        # regardless: current authority, dispatch, and
                        # Coordinator attribution are composed *around* a
                        # ModelPort call by an outer permitted consumer).
                        errors.add("intelligence-owner")
                    if name.startswith("legoai.intelligence.") and any(
                        target == f"legoai.intelligence.{layer}"
                        or target.startswith(f"legoai.intelligence.{layer}.")
                        for layer in ("reference", "runtime")
                    ):
                        errors.add("values-layer")
                    if name in {
                        "legoai.reference.model",
                        "legoai.reference.model_fake",
                    } and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.intelligence.model.values"
                        or target.startswith("legoai.intelligence.model.values.")
                        or target == "legoai.intelligence.model.ports"
                        or target.startswith("legoai.intelligence.model.ports.")
                        # ADR-002 SS9.2's I-row maximum includes C (Capabilities)
                        # and X (Plugins); this reference realization is the
                        # first real consumer of both, needed only to declare
                        # its own fixed Plugin/Capability identity functions
                        # for Catalog publication (mirrors
                        # legoai.reference.deterministic's identical pattern).
                        or target == "legoai.capabilities.values"
                        or target.startswith("legoai.capabilities.values.")
                        or target == "legoai.plugins.values"
                        or target.startswith("legoai.plugins.values.")
                    ):
                        # v0.1's reference realization gets the same
                        # allowed-peer permissions as its owner's row
                        # (ADR-002 SS9.2/SS7); it never imports another
                        # reference-owner realization or the composition root.
                        errors.add("reference-owner")
                    if name.startswith("legoai.runtime._composition.") and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.application.values"
                        or target.startswith("legoai.application.values.")
                        or target == "legoai.plugins.values"
                        or target.startswith("legoai.plugins.values.")
                        or target == "legoai.capabilities.values"
                        or target.startswith("legoai.capabilities.values.")
                        or target == "legoai.observability.values"
                        or target.startswith("legoai.observability.values.")
                        or target == "legoai.observability.ports"
                        or target.startswith("legoai.observability.ports.")
                        or target == "legoai.reference.declarations"
                        or target.startswith("legoai.reference.declarations.")
                        or target == "legoai.reference.resolution"
                        or target.startswith("legoai.reference.resolution.")
                        or target == "legoai.reference.deterministic"
                        or target.startswith("legoai.reference.deterministic.")
                        or target == "legoai.reference.application.configuration"
                        or target.startswith(
                            "legoai.reference.application.configuration."
                        )
                        # Gate-2 M11: the composition root is the sole
                        # location ADR-002 SS9.2 permits to import across
                        # both `legoai.application` and every
                        # `legoai.reference.*` module for wiring -- it is
                        # the first real consumer of `legoai.capabilities.
                        # ports` (CatalogEntry), `legoai.execution.ports`/
                        # `.values` and `legoai.reference.execution`
                        # (ExecutionCoordinator) needed to bind the one known
                        # trusted deterministic implementation to a governed
                        # invocation.
                        or target == "legoai.capabilities.ports"
                        or target.startswith("legoai.capabilities.ports.")
                        or target == "legoai.execution.ports"
                        or target.startswith("legoai.execution.ports.")
                        or target == "legoai.execution.values"
                        or target.startswith("legoai.execution.values.")
                        or target == "legoai.reference.execution"
                        or target.startswith("legoai.reference.execution.")
                        # v0.1: the composition root wires ModelPort-based
                        # governed invocation the same way it wired M11's
                        # pure fixture -- `legoai.intelligence.model.{values,
                        # ports}` and its own reference realization
                        # `legoai.reference.model` (the Ollama Adapter) are
                        # needed for exactly the same wiring reason.
                        or target == "legoai.intelligence.model.values"
                        or target.startswith("legoai.intelligence.model.values.")
                        or target == "legoai.intelligence.model.ports"
                        or target.startswith("legoai.intelligence.model.ports.")
                        or target == "legoai.reference.model"
                        or target.startswith("legoai.reference.model.")
                        or target == "legoai.intelligence.model.routing"
                        or target.startswith("legoai.intelligence.model.routing.")
                        or (
                            name == "legoai.runtime._composition.model_selection"
                            and (
                                target == "legoai.plugins.ports"
                                or target.startswith("legoai.plugins.ports.")
                            )
                        )
                        or (
                            name == "legoai.runtime._composition.agent"
                            and target.startswith("legoai.execution.agent.ports")
                        )
                        or target == "legoai.runtime"
                        or target.startswith("legoai.runtime._composition")
                    ):
                        # The private composition root may depend on lower
                        # reference realizations it actually needs (ADR-002
                        # SS4.2's "runtime private composition" row: "needed
                        # slice" of values/Ports plus "selected [reference]
                        # implementations"), but not on application.ports,
                        # the SQLite store/recovery realizations, or the
                        # concrete observation sink (F8b task SS41-42) --
                        # those remain the caller's own explicit choice.
                        errors.add("composition-owner")
                    if name == "legoai.runtime.api" and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or any(
                            target == f"legoai.{owner}"
                            or target.startswith(f"legoai.{owner}.")
                            for owner in (
                                "capabilities.values",
                                "execution.values",
                                "execution.agent.ports",
                                "governance.values",
                                "governance.ports",
                                "intelligence.model.values",
                                "intelligence.model.ports",
                                "intelligence.model.routing",
                                "plugins.values",
                            )
                        )
                    ):
                        # ADR-014 §3.1: the public facade is contract-only. It
                        # never imports reference realizations, private
                        # composition or its own composition entry module.
                        errors.add("runtime-api")
                elif root not in sys.stdlib_module_names:
                    errors.add("external")
                if target in sources:
                    edges[name].add(target)
                if f"{target}.__init__" in sources:
                    edges[name].add(f"{target}.__init__")

    def visit(name: str, active: set[str], done: set[str]) -> None:
        if name in active:
            errors.add("cycle")
            return
        if name in done:
            return
        active.add(name)
        for target in edges[name]:
            visit(target, active, done)
        active.remove(name)
        done.add(name)

    done: set[str] = set()
    for name in edges:
        visit(name, set(), done)
    return errors


def test_production_boundaries() -> None:
    root = Path(__file__).resolve().parents[2] / "src"
    sources = {
        ".".join(p.relative_to(root).with_suffix("").parts): p.read_text(
            encoding="utf-8"
        )
        for p in root.rglob("*.py")
    }
    assert sources
    assert violations(sources) == set()


@pytest.mark.parametrize(
    ("source", "reason"),
    [
        ("import legoai.reference", "kernel-owner"),
        ("from ..reference import adapter", "kernel-owner"),
        ("import tests.support", "test-import"),
        (
            "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n import legoai.runtime",
            "kernel-owner",
        ),
        ("from dataclasses import *", "star"),
        ("import importlib as loader", "dynamic"),
        ("__import__('legoai.reference')", "dynamic"),
        ("loader = __import__\nloader('legoai.reference')", "dynamic"),
        ("from builtins import __import__ as loader", "dynamic"),
        ("import ctypes", "dynamic"),
        ("import provider_sdk", "external"),
    ],
)
def test_checker_rejects(source: str, reason: str) -> None:
    assert reason in violations({"legoai.kernel.identity": source})


def test_reexport_and_initializer() -> None:
    assert violations(
        {
            "legoai.kernel.identity": "from .bridge import secret",
            "legoai.kernel.bridge": "from legoai.reference import secret",
            "legoai.__init__": "from legoai.kernel import identity",
        }
    ) == {"kernel-owner", "initializer"}


def test_cycle() -> None:
    assert "cycle" in violations(
        {"legoai.kernel.a": "from . import b", "legoai.kernel.b": "from . import a"}
    )


def test_valid_graph() -> None:
    assert not violations(
        {
            "legoai.__init__": '"""Inert."""',
            "legoai.kernel.identity": "from dataclasses import dataclass",
        }
    )


@pytest.mark.parametrize(
    "owner", ["application", "reference", "runtime", "resources.values"]
)
def test_governance_owner_boundary(owner: str) -> None:
    assert violations({"legoai.governance.values": f"import legoai.{owner}"}) == {
        "governance-owner"
    }


def test_kernel_cannot_import_governance() -> None:
    assert violations(
        {"legoai.kernel.context": "from legoai.governance.values import Principal"}
    ) == {"kernel-owner"}


def test_governance_values_cannot_import_ports_via_helper() -> None:
    assert "values-layer" in violations(
        {"legoai.governance.values": "from .ports import check"}
    )
    assert "governance-owner" in violations(
        {
            "legoai.governance.values": "from .pure import Principal",
            "legoai.governance.pure": "from legoai.resources.values import Balance",
        }
    )


def test_governance_inward_graph() -> None:
    assert not violations(
        {
            "legoai.governance.__init__": '"""Inert."""',
            "legoai.governance.values": "from legoai.kernel.context import TenantContext",
            "legoai.kernel.context": "from .identity import TenantId",
            "legoai.kernel.identity": "from dataclasses import dataclass",
        }
    )


def test_no_ambient_context_or_module_state() -> None:
    # Gate-2 M9 exception: `legoai.reference.execution` is allowed to import
    # `threading` for exactly one purpose -- an instance-scoped
    # `threading.Lock` inside `DeterministicDispatchArbiter` that implements
    # ADR-007 SS6.2's exclusive gate (no TOCTOU window between revalidating
    # current authorization/catalog/evidence and committing Approval-use
    # consumption). This is deliberately *not* ambient/module state: the
    # lock lives on the instance, is never read from module scope, and
    # every other file in this tree remains fully forbidden from importing
    # `threading`/`contextvars`.
    threading_import_allowed = {"legoai.reference.execution"}

    root = Path(__file__).resolve().parents[2] / "src" / "legoai"
    for path in root.rglob("*.py"):
        module_name = "legoai." + ".".join(path.relative_to(root).with_suffix("").parts)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert not any(
            isinstance(node, (ast.Assign, ast.AnnAssign)) for node in tree.body
        ), path
        assert not any(
            isinstance(node, (ast.Global, ast.Nonlocal)) for node in ast.walk(tree)
        ), path
        if module_name in threading_import_allowed:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not {alias.name.split(".")[0] for alias in node.names} & {
                    "contextvars",
                    "threading",
                }, path

            if isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in {
                    "contextvars",
                    "threading",
                }, path


@pytest.mark.parametrize(
    ("module", "source", "reason"),
    [
        (
            "legoai.application.values",
            "from legoai.reference.application import configuration",
            "application-owner",
        ),
        (
            "legoai.application.values",
            "from legoai.resources.values import Balance",
            "application-owner",
        ),
        ("legoai.application.values", "from .ports import Store", "values-layer"),
        (
            "legoai.reference.application.configuration",
            "import legoai.runtime",
            "reference-owner",
        ),
        (
            "legoai.reference.application.configuration",
            "import legoai.reference.governance",
            "reference-owner",
        ),
        (
            "legoai.reference.application.configuration",
            "import provider_sdk",
            "external",
        ),
        ("legoai.kernel.context", "import legoai.application.values", "kernel-owner"),
    ],
)
def test_f2_boundaries(module: str, source: str, reason: str) -> None:
    assert reason in violations({module: source})


def test_f2_cycle_and_indirect_import() -> None:
    assert {"application-owner", "cycle"} <= violations(
        {
            "legoai.application.values": "from .helper import Value",
            "legoai.application.helper": "from legoai.reference.application.configuration import compose",
            "legoai.reference.application.configuration": "from legoai.application.values import Value",
        }
    )


def test_f2_pure_module_dependencies() -> None:
    # Scoped to reference/application/configuration.py only: F4 deliberately
    # extends application/values.py beyond F2's original pure-fixture scope
    # (it now legitimately imports OwnerRevision/ConfigurationRevisionRef for
    # the operation/result/duty model) -- see test_f4_boundaries below for
    # values.py's own, F4-scoped import constraints.
    root = Path(__file__).resolve().parents[2] / "src" / "legoai"
    for relative in ("reference/application/configuration.py",):
        tree = ast.parse((root / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] in {
                    "dataclasses",
                    "enum",
                    "typing",
                    "legoai",
                }
                assert not {alias.name for alias in node.names} & {
                    "OwnerRevision",
                    "ConfigurationRevisionRef",
                    "OperationContext",
                }
            if isinstance(node, ast.Import):
                assert all(
                    alias.name.split(".")[0]
                    in {"dataclasses", "enum", "typing", "legoai"}
                    for alias in node.names
                )
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"open", "print", "input"}


# --- F4: evidence-owner boundary, and application's widened (but still
# narrow) access to evidence/governance -----------------------------------


@pytest.mark.parametrize(
    "owner", ["application", "reference", "runtime", "resources.values", "capabilities"]
)
def test_evidence_owner_boundary(owner: str) -> None:
    assert violations({"legoai.evidence.values": f"import legoai.{owner}"}) == {
        "evidence-owner"
    }


def test_evidence_values_cannot_import_ports_via_helper() -> None:
    assert "values-layer" in violations(
        {"legoai.evidence.values": "from .ports import check"}
    )
    assert "evidence-owner" in violations(
        {
            "legoai.evidence.values": "from .pure import Requirement",
            "legoai.evidence.pure": "from legoai.governance.values import Principal",
        }
    )


def test_evidence_inward_graph() -> None:
    assert not violations(
        {
            "legoai.evidence.__init__": '"""Inert."""',
            "legoai.evidence.values": "from legoai.kernel.references import ConfigurationRevisionRef",
            "legoai.kernel.references": "from .identity import ApplicationId",
            "legoai.kernel.identity": "from dataclasses import dataclass",
        }
    )


def test_kernel_cannot_import_evidence() -> None:
    assert violations(
        {
            "legoai.kernel.provenance": "from legoai.evidence.values import EvidenceRequirement"
        }
    ) == {"kernel-owner"}


# --- Gate-2 M8: evidence.ports (custody) and reference.evidence boundaries -


@pytest.mark.parametrize("owner", ["application", "runtime", "execution", "resources"])
def test_evidence_ports_owner_boundary(owner: str) -> None:
    assert violations({"legoai.evidence.ports": f"import legoai.{owner}"}) == {
        "evidence-owner"
    }


def test_evidence_ports_may_depend_on_own_values_and_governance() -> None:
    assert "evidence-owner" not in violations(
        {
            "legoai.evidence.ports": "from legoai.evidence.values import EvidenceRequirement"
        }
    )
    assert "evidence-owner" not in violations(
        {"legoai.evidence.ports": "from legoai.governance.values import Principal"}
    )
    assert "evidence-owner" not in violations(
        {
            "legoai.evidence.ports": "from legoai.governance.ports import AuthorizationDecision"
        }
    )


def test_evidence_values_does_not_gain_governance_widening() -> None:
    # Only legoai.evidence.ports (the M8 custody layer) is widened to
    # Governance; legoai.evidence.values keeps F4's original, narrower
    # Kernel-only permission set.
    assert "evidence-owner" in violations(
        {"legoai.evidence.values": "from legoai.governance.values import Principal"}
    )


def test_reference_evidence_may_depend_on_own_port_values_and_governance() -> None:
    assert "reference-owner" not in violations(
        {
            "legoai.reference.evidence": "from legoai.evidence.ports import EvidenceRecord"
        }
    )
    assert "reference-owner" not in violations(
        {
            "legoai.reference.evidence": "from legoai.evidence.values import EvidenceRequirement"
        }
    )


def test_reference_evidence_cannot_import_other_reference_realizations() -> None:
    assert "reference-owner" in violations(
        {"legoai.reference.evidence": "import legoai.reference.governance"}
    )
    assert "reference-owner" in violations(
        {"legoai.reference.evidence": "import legoai.reference.catalog"}
    )
    assert "reference-owner" in violations(
        {
            "legoai.reference.evidence": "from legoai.observability.values import Observation"
        }
    )


def test_reference_evidence_does_not_leak_test_fake() -> None:
    assert "test-import" in violations(
        {
            "legoai.reference.evidence": "from tests.support.governance import InMemoryGrantStateFake"
        }
    )


@pytest.mark.parametrize(
    "module",
    [
        "legoai.execution.values",
        "legoai.governance.values",
        "legoai.resources.values",
        "legoai.plugins.values",
        "legoai.capabilities.values",
    ],
)
def test_semantic_values_do_not_depend_on_evidence_custody(module: str) -> None:
    reason_by_module = {
        "legoai.execution.values": "execution-owner",
        "legoai.governance.values": "governance-owner",
        "legoai.resources.values": "resources-owner",
        "legoai.plugins.values": "plugins-owner",
        "legoai.capabilities.values": "capabilities-owner",
    }
    assert reason_by_module[module] in violations(
        {module: "from legoai.evidence.ports import EvidenceRecord"}
    )
    assert reason_by_module[module] in violations(
        {module: "from legoai.reference.evidence import InMemoryEvidenceCustody"}
    )


@pytest.mark.parametrize(
    ("module", "source", "reason"),
    [
        (
            "legoai.application.values",
            "from legoai.evidence.values import EvidenceRequirement",
            None,
        ),
        (
            "legoai.application.values",
            "from legoai.governance.values import Principal",
            None,
        ),
        (
            "legoai.application.values",
            "from legoai.capabilities.values import Requirement",
            "application-owner",
        ),
        (
            "legoai.application.values",
            "from legoai.execution.values import ExecutionId",
            "application-owner",
        ),
        (
            "legoai.application.values",
            "from legoai.plugins.values import PluginId",
            "application-owner",
        ),
    ],
)
def test_f4_boundaries(module: str, source: str, reason: str | None) -> None:
    result = violations({module: source})
    if reason is None:
        assert "application-owner" not in result
    else:
        assert reason in result


def test_application_ports_does_not_depend_on_reference_implementation() -> None:
    assert "application-owner" in violations(
        {
            "legoai.application.ports": "from legoai.reference.application import configuration"
        }
    )


def test_test_support_configuration_store_is_rejected_as_production_import() -> None:
    assert "test-import" in violations(
        {
            "legoai.application.values": "from tests.support.configuration_store import InMemoryConfigurationStore"
        }
    )


def test_no_database_driver_imported_by_production_source() -> None:
    # sqlite3 is stdlib, so the generic "external" check does not catch it.
    # F6a's store and F6b's recovery inspection are the two authorized
    # modules allowed to use it (stdlib only, zero new dependencies); every
    # other production module -- including F5's codec, which is
    # representation-only -- must stay database-free, and no non-stdlib
    # driver/ORM is ever permitted anywhere.
    allowed_sqlite3_paths = {
        "reference/application/sqlite_store.py",
        "reference/application/recovery.py",
    }
    forbidden_everywhere_roots = {
        "psycopg",
        "psycopg2",
        "asyncpg",
        "sqlalchemy",
        "pymongo",
        "redis",
        "aiosqlite",
        "peewee",
        "dataset",
    }
    root = Path(__file__).resolve().parents[2] / "src" / "legoai"
    offenders: dict[str, set[str]] = {}
    for path in root.rglob("*.py"):
        relative = str(path.relative_to(root)).replace("\\", "/")
        forbidden_here = set(forbidden_everywhere_roots)
        if relative not in allowed_sqlite3_paths:
            forbidden_here.add("sqlite3")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found |= {alias.name.split(".")[0] for alias in node.names} & (
                    forbidden_here
                )
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in forbidden_here:
                    found.add(node.module.split(".")[0])
        if found:
            offenders[relative] = found
    assert offenders == {}


def test_no_ai_or_agent_framework_imported_by_production_source() -> None:
    forbidden_ai_roots = {
        "semantic_kernel",
        "agent_framework",
        "openai",
        "anthropic",
        "ollama",
        "langchain",
        "langgraph",
    }
    root = Path(__file__).resolve().parents[2] / "src" / "legoai"
    offenders: dict[str, set[str]] = {}
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found |= {
                    alias.name.split(".")[0] for alias in node.names
                } & forbidden_ai_roots
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in forbidden_ai_roots:
                    found.add(node.module.split(".")[0])
        if found:
            offenders[str(path.relative_to(root))] = found
    assert offenders == {}


def test_no_documind_or_document_pack_import_by_core() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "legoai"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            roots: set[str] = set()
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots = {node.module.split(".")[0]}
            if roots & {"legoai_document", "documind"}:
                offenders.append(str(path.relative_to(root)))
    assert offenders == []


def test_core_does_not_import_collation_pack() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "legoai"
    sources = list(root.rglob("*.py"))
    assert sources, "Core source tree is missing"
    offenders: list[str] = []
    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            roots: set[str] = set()
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots = {node.module.split(".")[0]}
            if "legoai_collation" in roots:
                offenders.append(str(path.relative_to(root)))
    assert offenders == []


# --- F5: reference-persistence codec boundary -----------------------------


@pytest.mark.parametrize(
    ("module", "source", "reason"),
    [
        (
            "legoai.application.values",
            "from legoai.reference.application.codec import encode_owner_head",
            "application-owner",
        ),
        (
            "legoai.evidence.values",
            "from legoai.reference.application.codec import encode_owner_head",
            "evidence-owner",
        ),
        (
            "legoai.governance.values",
            "from legoai.reference.application.codec import encode_owner_head",
            "governance-owner",
        ),
        (
            "legoai.kernel.provenance",
            "from legoai.reference.application.codec import encode_owner_head",
            "kernel-owner",
        ),
    ],
)
def test_f5_semantic_packages_do_not_depend_on_reference_codec(
    module: str, source: str, reason: str
) -> None:
    # F5's codec is an implementation detail of the Application Composition
    # owner's *reference realization*; no canonical value module may import
    # it, in either direction of the values/reference layering (ADR-002 SS7).
    assert reason in violations({module: source})


@pytest.mark.parametrize(
    "source",
    [
        "from legoai.application.values import OwnerRevision",
        "from legoai.governance.values import Principal",
        "from legoai.evidence.values import EvidenceRequirement",
        "from legoai.kernel.references import ConfigurationRef",
    ],
)
def test_f5_reference_codec_may_depend_inward_on_allowed_peer_values(
    source: str,
) -> None:
    # Mirrors the owner's own allowed-peer widening (ADR-002 SS9.2): a
    # reference realization gets the same foreign-value permissions as the
    # owner it realizes.
    assert "reference-owner" not in violations(
        {"legoai.reference.application.codec": source}
    )


def test_f5_reference_codec_cannot_import_ports_or_other_reference_owners() -> None:
    assert "reference-owner" in violations(
        {
            "legoai.reference.application.codec": "from legoai.application.ports import ConfigurationStorePort"
        }
    )
    assert "reference-owner" in violations(
        {"legoai.reference.application.codec": "import legoai.reference.governance"}
    )


def test_f5_codec_does_not_leak_test_fake() -> None:
    assert "test-import" in violations(
        {
            "legoai.reference.application.codec": "from tests.support.configuration_store import InMemoryConfigurationStore"
        }
    )


# --- F6b: recovery/qualification boundary ---------------------------------


@pytest.mark.parametrize(
    ("module", "source", "reason"),
    [
        (
            "legoai.application.values",
            "from legoai.reference.application.recovery import qualify_store",
            "application-owner",
        ),
        (
            "legoai.evidence.values",
            "from legoai.reference.application.recovery import qualify_store",
            "evidence-owner",
        ),
        (
            "legoai.governance.values",
            "from legoai.reference.application.recovery import qualify_store",
            "governance-owner",
        ),
        (
            "legoai.kernel.provenance",
            "from legoai.reference.application.recovery import qualify_store",
            "kernel-owner",
        ),
    ],
)
def test_f6b_semantic_packages_do_not_depend_on_recovery(
    module: str, source: str, reason: str
) -> None:
    # Recovery is an inspection/qualification detail of the reference
    # realization; no canonical value module may import it.
    assert reason in violations({module: source})


@pytest.mark.parametrize(
    "source",
    [
        "from legoai.reference.application.sqlite_store import SQLiteConfigurationStore",
        "from legoai.reference.application.codec import decode_publication_result",
        "from legoai.application.values import OwnerRevision",
        "from legoai.evidence.values import EvidenceRequirement",
        "from legoai.kernel.references import ConfigurationRef",
    ],
)
def test_f6b_recovery_may_depend_inward_on_store_codec_and_allowed_values(
    source: str,
) -> None:
    assert "reference-owner" not in violations(
        {"legoai.reference.application.recovery": source}
    )


def test_f6b_recovery_cannot_import_ports_directly() -> None:
    # Recovery inspects through the concrete SQLite realization's own public
    # methods, not the abstract Port -- it never needed to import it, so the
    # module-suffix exception granted to "_store" modules does not apply here.
    assert "reference-owner" in violations(
        {
            "legoai.reference.application.recovery": "from legoai.application.ports import ConfigurationStorePort"
        }
    )


def test_f6b_recovery_cannot_import_other_reference_owners() -> None:
    assert "reference-owner" in violations(
        {"legoai.reference.application.recovery": "import legoai.reference.governance"}
    )


def test_f6b_recovery_does_not_leak_test_fake() -> None:
    assert "test-import" in violations(
        {
            "legoai.reference.application.recovery": "from tests.support.configuration_store import InMemoryConfigurationStore"
        }
    )


# --- F8a: observability owner and reference.observation boundary ----------


def test_kernel_cannot_import_observability() -> None:
    assert violations(
        {"legoai.kernel.errors": "from legoai.observability.values import Observation"}
    ) == {"kernel-owner"}


@pytest.mark.parametrize(
    "owner", ["application", "reference", "runtime", "resources.values", "evidence"]
)
def test_observability_owner_boundary(owner: str) -> None:
    assert violations({"legoai.observability.values": f"import legoai.{owner}"}) == {
        "observability-owner"
    }


def test_observability_values_cannot_import_ports_via_helper() -> None:
    assert "values-layer" in violations(
        {"legoai.observability.values": "from .ports import check"}
    )
    assert "observability-owner" in violations(
        {
            "legoai.observability.values": "from .pure import Observation",
            "legoai.observability.pure": "from legoai.governance.values import Principal",
        }
    )


def test_observability_inward_graph() -> None:
    assert not violations(
        {
            "legoai.observability.__init__": '"""Inert."""',
            "legoai.observability.values": "from legoai.kernel.errors import ErrorCategory",
            "legoai.kernel.errors": "from .identity import _validate",
            "legoai.kernel.identity": "from dataclasses import dataclass",
        }
    )


@pytest.mark.parametrize(
    ("module", "source", "reason"),
    [
        (
            "legoai.application.values",
            "from legoai.reference.observation import LocalLoggingObservationSink",
            "application-owner",
        ),
        (
            "legoai.evidence.values",
            "from legoai.reference.observation import LocalLoggingObservationSink",
            "evidence-owner",
        ),
        (
            "legoai.governance.values",
            "from legoai.reference.observation import LocalLoggingObservationSink",
            "governance-owner",
        ),
        (
            "legoai.kernel.provenance",
            "from legoai.reference.observation import LocalLoggingObservationSink",
            "kernel-owner",
        ),
    ],
)
def test_f8a_semantic_packages_do_not_depend_on_reference_observation(
    module: str, source: str, reason: str
) -> None:
    assert reason in violations({module: source})


@pytest.mark.parametrize(
    "source",
    [
        "from legoai.observability.values import Observation",
        "from legoai.observability.ports import ObservationSinkPort",
        "from legoai.kernel.errors import ErrorCategory",
    ],
)
def test_f8a_reference_observation_may_depend_on_its_own_port_and_values(
    source: str,
) -> None:
    assert "reference-owner" not in violations({"legoai.reference.observation": source})


def test_f8a_reference_observation_cannot_import_other_reference_realizations() -> None:
    assert "reference-owner" in violations(
        {
            "legoai.reference.observation": "from legoai.reference.application.sqlite_store import SQLiteConfigurationStore"
        }
    )
    assert "reference-owner" in violations(
        {"legoai.reference.observation": "import legoai.reference.governance"}
    )
    assert "reference-owner" in violations(
        {
            "legoai.reference.observation": "from legoai.application.ports import ConfigurationStorePort"
        }
    )


def test_f8a_reference_observation_does_not_leak_test_fake() -> None:
    assert "test-import" in violations(
        {
            "legoai.reference.observation": "from tests.support.observation import CapturingObservationSink"
        }
    )


# --- Gate-2 M4: reference.governance boundary -------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "from legoai.governance.values import Grant",
        "from legoai.governance.ports import AuthorizationPort",
        "from legoai.kernel.errors import ErrorCategory",
    ],
)
def test_reference_governance_may_depend_on_its_own_port_and_values(
    source: str,
) -> None:
    assert "reference-owner" not in violations({"legoai.reference.governance": source})


def test_reference_governance_cannot_import_other_reference_realizations() -> None:
    assert "reference-owner" in violations(
        {
            "legoai.reference.governance": "from legoai.reference.application.sqlite_store import SQLiteConfigurationStore"
        }
    )
    assert "reference-owner" in violations(
        {"legoai.reference.governance": "import legoai.reference.resolution"}
    )
    assert "reference-owner" in violations(
        {
            "legoai.reference.governance": "from legoai.observability.values import Observation"
        }
    )


def test_reference_governance_does_not_leak_test_fake() -> None:
    assert "test-import" in violations(
        {
            "legoai.reference.governance": "from tests.support.governance import InMemoryGrantStateFake"
        }
    )


# --- Gate-2 M5: reference.plugins (lifecycle) boundary ----------------------


@pytest.mark.parametrize(
    "source",
    [
        "from legoai.plugins.values import PluginDeclaration",
        "from legoai.plugins.ports import PluginLifecycleRecord",
        "from legoai.kernel.context import TenantContext",
    ],
)
def test_reference_plugins_may_depend_on_its_own_port_and_values(source: str) -> None:
    assert "reference-owner" not in violations({"legoai.reference.plugins": source})


def test_reference_plugins_cannot_import_other_reference_realizations() -> None:
    assert "reference-owner" in violations(
        {"legoai.reference.plugins": "import legoai.reference.governance"}
    )
    assert "reference-owner" in violations(
        {"legoai.reference.plugins": "from legoai.governance.values import Grant"}
    )
    assert "reference-owner" in violations(
        {
            "legoai.reference.plugins": "from legoai.capabilities.values import CapabilityId"
        }
    )


def test_reference_plugins_does_not_leak_test_fake() -> None:
    assert "test-import" in violations(
        {
            "legoai.reference.plugins": "from tests.support.governance import InMemoryGrantStateFake"
        }
    )


# --- F7: capabilities/plugins owner boundaries and reference analysis -----


def test_kernel_cannot_import_capabilities_or_plugins() -> None:
    assert violations(
        {"legoai.kernel.errors": "from legoai.capabilities.values import CapabilityId"}
    ) == {"kernel-owner"}
    assert violations(
        {"legoai.kernel.errors": "from legoai.plugins.values import PluginId"}
    ) == {"kernel-owner"}


@pytest.mark.parametrize(
    "owner", ["application", "reference", "runtime", "plugins", "evidence"]
)
def test_capabilities_owner_boundary(owner: str) -> None:
    assert violations({"legoai.capabilities.values": f"import legoai.{owner}"}) == {
        "capabilities-owner"
    }


def test_capabilities_does_not_depend_on_plugins() -> None:
    assert "capabilities-owner" in violations(
        {"legoai.capabilities.values": "from legoai.plugins.values import PluginId"}
    )


def test_capabilities_values_cannot_import_ports_via_helper() -> None:
    assert "values-layer" in violations(
        {"legoai.capabilities.values": "from .ports import check"}
    )


def test_capabilities_inward_graph() -> None:
    assert not violations(
        {
            "legoai.capabilities.__init__": '"""Inert."""',
            "legoai.capabilities.values": "from legoai.kernel.versions import Version",
            "legoai.kernel.versions": "from dataclasses import dataclass",
        }
    )


# --- Gate-2 M6: capabilities.ports (Catalog) and reference.catalog boundaries -


@pytest.mark.parametrize("owner", ["application", "runtime", "governance", "evidence"])
def test_capabilities_ports_owner_boundary(owner: str) -> None:
    assert violations({"legoai.capabilities.ports": f"import legoai.{owner}"}) == {
        "capabilities-owner"
    }


def test_capabilities_ports_may_depend_on_own_values_and_plugins() -> None:
    assert "capabilities-owner" not in violations(
        {
            "legoai.capabilities.ports": "from legoai.capabilities.values import CapabilityOffer"
        }
    )
    assert "capabilities-owner" not in violations(
        {"legoai.capabilities.ports": "from legoai.plugins.values import PluginId"}
    )
    assert "capabilities-owner" not in violations(
        {
            "legoai.capabilities.ports": "from legoai.plugins.ports import PluginLifecycleRecord"
        }
    )


def test_capabilities_ports_cannot_import_execution_or_resources() -> None:
    assert "capabilities-owner" in violations(
        {"legoai.capabilities.ports": "from legoai.execution.values import ExecutionId"}
    )
    assert "capabilities-owner" in violations(
        {
            "legoai.capabilities.ports": "from legoai.resources.values import ResourceClaim"
        }
    )


def test_reference_catalog_may_depend_on_own_port_values_and_plugins() -> None:
    assert "reference-owner" not in violations(
        {
            "legoai.reference.catalog": "from legoai.capabilities.ports import CatalogEntry"
        }
    )
    assert "reference-owner" not in violations(
        {
            "legoai.reference.catalog": "from legoai.plugins.ports import PluginLifecycleRecord"
        }
    )


def test_reference_catalog_cannot_import_other_reference_realizations() -> None:
    assert "reference-owner" in violations(
        {"legoai.reference.catalog": "import legoai.reference.governance"}
    )
    assert "reference-owner" in violations(
        {"legoai.reference.catalog": "import legoai.reference.plugins"}
    )
    assert "reference-owner" in violations(
        {"legoai.reference.catalog": "from legoai.governance.values import Grant"}
    )


def test_reference_catalog_does_not_leak_test_fake() -> None:
    assert "test-import" in violations(
        {
            "legoai.reference.catalog": "from tests.support.governance import InMemoryGrantStateFake"
        }
    )


@pytest.mark.parametrize(
    "module",
    [
        "legoai.execution.values",
        "legoai.governance.values",
        "legoai.resources.values",
        "legoai.plugins.values",
        "legoai.capabilities.values",
    ],
)
def test_semantic_values_do_not_depend_on_catalog(module: str) -> None:
    reason_by_module = {
        "legoai.execution.values": "execution-owner",
        "legoai.governance.values": "governance-owner",
        "legoai.resources.values": "resources-owner",
        "legoai.plugins.values": "plugins-owner",
        "legoai.capabilities.values": "capabilities-owner",
    }
    assert reason_by_module[module] in violations(
        {module: "from legoai.capabilities.ports import CatalogEntry"}
    )
    assert reason_by_module[module] in violations(
        {module: "from legoai.reference.catalog import InMemoryCatalog"}
    )


@pytest.mark.parametrize("owner", ["application", "reference", "runtime", "evidence"])
def test_plugins_owner_boundary(owner: str) -> None:
    assert violations({"legoai.plugins.values": f"import legoai.{owner}"}) == {
        "plugins-owner"
    }


def test_plugins_may_depend_on_capabilities_values() -> None:
    assert "plugins-owner" not in violations(
        {"legoai.plugins.values": "from legoai.capabilities.values import CapabilityId"}
    )


def test_plugins_values_cannot_import_ports_or_spi_via_helper() -> None:
    assert "values-layer" in violations(
        {"legoai.plugins.values": "from .ports import check"}
    )
    assert "values-layer" in violations(
        {"legoai.plugins.values": "from .spi import author_hook"}
    )


# --- Gate-2 M1: execution owner boundary -----------------------------------


def test_kernel_cannot_import_execution() -> None:
    assert violations(
        {"legoai.kernel.errors": "from legoai.execution.values import ExecutionId"}
    ) == {"kernel-owner"}


@pytest.mark.parametrize(
    "owner",
    [
        "application",
        "reference",
        "runtime",
        "governance",
        "capabilities",
        "plugins",
        "evidence",
    ],
)
def test_execution_owner_boundary(owner: str) -> None:
    assert violations({"legoai.execution.values": f"import legoai.{owner}"}) == {
        "execution-owner"
    }


def test_execution_values_does_not_import_governance_values() -> None:
    # ADR-002 SS9's values.py rule: "It does not import another owner's
    # values" -- even though ADR-002 SS9.2's E-row maximum lists G as an
    # allowed foreign *contract* target for a future ports.py, values.py
    # itself may never embed a foreign owner's value (e.g. Principal).
    assert "execution-owner" in violations(
        {"legoai.execution.values": "from legoai.governance.values import Principal"}
    )


def test_execution_values_cannot_import_ports_via_helper() -> None:
    assert "values-layer" in violations(
        {"legoai.execution.values": "from .ports import check"}
    )


def test_execution_inward_graph() -> None:
    assert not violations(
        {
            "legoai.execution.__init__": '"""Inert."""',
            "legoai.execution.values": "from legoai.kernel.effects import EffectExtent",
            "legoai.kernel.effects": "from enum import Enum",
        }
    )


# --- Gate-2 M3: resources owner boundary -----------------------------------


def test_kernel_cannot_import_resources() -> None:
    assert violations(
        {
            "legoai.kernel.errors": "from legoai.resources.values import ResourceDimension"
        }
    ) == {"kernel-owner"}


@pytest.mark.parametrize(
    "owner",
    [
        "application",
        "reference",
        "runtime",
        "governance",
        "execution",
        "capabilities",
        "plugins",
        "evidence",
        "observability",
    ],
)
def test_resources_owner_boundary(owner: str) -> None:
    assert violations({"legoai.resources.values": f"import legoai.{owner}"}) == {
        "resources-owner"
    }


def test_resources_values_does_not_import_governance_or_execution_values() -> None:
    # ADR-002 SS9's values.py rule applies here exactly as it did for
    # execution.values (M1) and governance.values (M2): even though the
    # R-row's foreign-*contract*-target maximum (SS9.2) includes G, that
    # maximum is for a future ports.py, not this owner's values module.
    assert "resources-owner" in violations(
        {"legoai.resources.values": "from legoai.governance.values import Grant"}
    )
    assert "resources-owner" in violations(
        {"legoai.resources.values": "from legoai.execution.values import ExecutionId"}
    )


def test_execution_and_governance_values_do_not_depend_on_resources() -> None:
    assert "execution-owner" in violations(
        {"legoai.execution.values": "from legoai.resources.values import ResourceClaim"}
    )
    assert "governance-owner" in violations(
        {
            "legoai.governance.values": "from legoai.resources.values import ResourceClaim"
        }
    )


def test_resources_values_cannot_import_ports_via_helper() -> None:
    assert "values-layer" in violations(
        {"legoai.resources.values": "from .ports import check"}
    )


def test_resources_inward_graph() -> None:
    assert not violations(
        {
            "legoai.resources.__init__": '"""Inert."""',
            "legoai.resources.values": "from legoai.kernel.versions import Version",
            "legoai.kernel.versions": "from dataclasses import dataclass",
        }
    )


def test_plugins_inward_graph() -> None:
    assert not violations(
        {
            "legoai.plugins.__init__": '"""Inert."""',
            "legoai.plugins.values": "from legoai.capabilities.values import CapabilityId",
            "legoai.capabilities.__init__": '"""Inert."""',
            "legoai.capabilities.values": "from legoai.kernel.versions import Version",
            "legoai.kernel.versions": "from dataclasses import dataclass",
        }
    )


@pytest.mark.parametrize(
    ("module", "source", "reason"),
    [
        (
            "legoai.application.values",
            "from legoai.reference.resolution import analyze_compatibility",
            "application-owner",
        ),
        (
            "legoai.evidence.values",
            "from legoai.reference.resolution import analyze_compatibility",
            "evidence-owner",
        ),
        (
            "legoai.governance.values",
            "from legoai.reference.resolution import analyze_compatibility",
            "governance-owner",
        ),
        (
            "legoai.kernel.provenance",
            "from legoai.reference.declarations import normalize_declarations",
            "kernel-owner",
        ),
    ],
)
def test_f7_semantic_packages_do_not_depend_on_reference_analysis(
    module: str, source: str, reason: str
) -> None:
    assert reason in violations({module: source})


@pytest.mark.parametrize(
    "source",
    [
        "from legoai.plugins.values import PluginDeclaration",
        "from legoai.capabilities.values import CapabilityRequirement",
        "from legoai.kernel.versions import Version",
    ],
)
def test_f7_reference_resolution_may_depend_on_plugin_and_capability_values(
    source: str,
) -> None:
    assert "reference-owner" not in violations({"legoai.reference.resolution": source})
    assert "reference-owner" not in violations(
        {"legoai.reference.declarations": source}
    )


def test_f7_reference_modules_cannot_import_other_reference_realizations() -> None:
    assert "reference-owner" in violations(
        {
            "legoai.reference.resolution": "from legoai.reference.application.sqlite_store import SQLiteConfigurationStore"
        }
    )
    assert "reference-owner" in violations(
        {
            "legoai.reference.resolution": "from legoai.reference.observation import LocalLoggingObservationSink"
        }
    )
    assert "reference-owner" in violations(
        {
            "legoai.reference.declarations": "from legoai.application.ports import ConfigurationStorePort"
        }
    )


def test_f7_reference_modules_do_not_leak_test_fake() -> None:
    assert "test-import" in violations(
        {
            "legoai.reference.resolution": "from tests.support.observation import CapturingObservationSink"
        }
    )
    assert "test-import" in violations(
        {
            "legoai.reference.declarations": "from tests.support.configuration_store import InMemoryConfigurationStore"
        }
    )


# --- Gate-2 M7: runtime resolution (legoai.reference.resolution) widening --


def test_reference_resolution_may_depend_on_capabilities_ports() -> None:
    assert "reference-owner" not in violations(
        {
            "legoai.reference.resolution": "from legoai.capabilities.ports import CatalogEntry"
        }
    )


def test_reference_declarations_does_not_gain_capabilities_ports_widening() -> None:
    # Only legoai.reference.resolution (the M7 runtime resolver) is widened;
    # legoai.reference.declarations has no M7 consumer and keeps F7's
    # original, narrower permission set.
    assert "reference-owner" in violations(
        {
            "legoai.reference.declarations": "from legoai.capabilities.ports import CatalogEntry"
        }
    )


def test_reference_resolution_cannot_import_catalog_realization() -> None:
    assert "reference-owner" in violations(
        {"legoai.reference.resolution": "import legoai.reference.catalog"}
    )
    assert "reference-owner" in violations(
        {
            "legoai.reference.resolution": "from legoai.reference.catalog import InMemoryCatalog"
        }
    )


@pytest.mark.parametrize(
    "module",
    [
        "legoai.execution.values",
        "legoai.governance.values",
        "legoai.resources.values",
        "legoai.plugins.values",
        "legoai.capabilities.values",
    ],
)
def test_semantic_values_do_not_depend_on_runtime_resolution(module: str) -> None:
    reason_by_module = {
        "legoai.execution.values": "execution-owner",
        "legoai.governance.values": "governance-owner",
        "legoai.resources.values": "resources-owner",
        "legoai.plugins.values": "plugins-owner",
        "legoai.capabilities.values": "capabilities-owner",
    }
    assert reason_by_module[module] in violations(
        {module: "from legoai.reference.resolution import resolve"}
    )


# --- F8b: private composition root and deterministic fixture boundary -----


@pytest.mark.parametrize(
    "owner",
    [
        "reference.application.sqlite_store",
        "reference.application.recovery",
        "reference.observation",
    ],
)
def test_reference_deterministic_cannot_import_other_reference_realizations(
    owner: str,
) -> None:
    assert "reference-owner" in violations(
        {"legoai.reference.deterministic": f"import legoai.{owner}"}
    )


def test_reference_deterministic_cannot_import_composition_root() -> None:
    assert "reference-owner" in violations(
        {
            "legoai.reference.deterministic": "from legoai.runtime._composition.direct import compose_direct"
        }
    )


def test_reference_deterministic_may_depend_on_needed_values() -> None:
    for source in (
        "from legoai.application.values import EffectiveConfiguration",
        "from legoai.capabilities.values import CapabilityId",
        "from legoai.plugins.values import PluginId",
        "from legoai.kernel.versions import Version",
    ):
        assert "reference-owner" not in violations(
            {"legoai.reference.deterministic": source}
        )


@pytest.mark.parametrize(
    "owner",
    [
        "application.ports",
        "reference.application.sqlite_store",
        "reference.application.recovery",
        "reference.observation",
    ],
)
def test_composition_root_cannot_import_ports_or_concrete_realizations(
    owner: str,
) -> None:
    assert "composition-owner" in violations(
        {"legoai.runtime._composition.direct": f"import legoai.{owner}"}
    )


def test_composition_root_may_depend_on_needed_reference_and_semantic_pieces() -> None:
    for source in (
        "from legoai.application.values import ComposedConfiguration",
        "from legoai.capabilities.values import CapabilityRequirement",
        "from legoai.plugins.values import PluginDeclaration",
        "from legoai.observability.values import Observation",
        "from legoai.observability.ports import ObservationSinkPort",
        "from legoai.reference.declarations import normalize_declarations",
        "from legoai.reference.resolution import analyze_compatibility",
        "from legoai.reference.deterministic import normalize_text",
        "from legoai.reference.application.configuration import compose_configuration",
        "from legoai.kernel.references import ConfigurationRef",
    ):
        assert "composition-owner" not in violations(
            {"legoai.runtime._composition.direct": source}
        )


def test_composition_root_does_not_leak_test_fake() -> None:
    assert "test-import" in violations(
        {
            "legoai.runtime._composition.direct": "from tests.support.observation import CapturingObservationSink"
        }
    )


@pytest.mark.parametrize(
    "owner",
    [
        "application.values",
        "capabilities.values",
        "plugins.values",
        "observability.values",
        "kernel.errors",
        "evidence.values",
        "governance.values",
        "execution.values",
        "resources.values",
        "capabilities.ports",
        "evidence.ports",
    ],
)
def test_no_semantic_package_depends_on_composition_root(owner: str) -> None:
    reason_by_owner = {
        "application.values": "application-owner",
        "capabilities.values": "capabilities-owner",
        "plugins.values": "plugins-owner",
        "observability.values": "observability-owner",
        "kernel.errors": "kernel-owner",
        "evidence.values": "evidence-owner",
        "governance.values": "governance-owner",
        "execution.values": "execution-owner",
        "resources.values": "resources-owner",
        "capabilities.ports": "capabilities-owner",
        "evidence.ports": "evidence-owner",
    }
    assert reason_by_owner[owner] in violations(
        {
            f"legoai.{owner}": "from legoai.runtime._composition.direct import compose_direct"
        }
    )


@pytest.mark.parametrize(
    "module",
    [
        "legoai.reference.declarations",
        "legoai.reference.resolution",
        "legoai.reference.deterministic",
        "legoai.reference.observation",
        "legoai.reference.governance",
        "legoai.reference.plugins",
        "legoai.reference.catalog",
        "legoai.reference.evidence",
        "legoai.reference.execution",
        "legoai.reference.model",
    ],
)
def test_reference_modules_do_not_depend_on_composition_root(module: str) -> None:
    assert "reference-owner" in violations(
        {module: "from legoai.runtime._composition.direct import compose_direct"}
    )


# --- Gate-2 M10: Coordinator/asyncio confinement ----------------------------


def test_asyncio_confined_to_authorized_reference_execution_module() -> None:
    """ADR-015's structured-concurrency substrate belongs to exactly the
    Coordinator (`legoai.reference.execution`) plus, as of v0.1, the one
    Adapter that bridges a genuinely blocking network call into it
    (`legoai.reference.model`, via `asyncio.to_thread` -- see that module's
    own docstring: the smallest possible bridge, never a general worker
    pool). No Kernel, values, Port or other reference/runtime module may
    import `asyncio` -- Coordinator/supervision behavior never leaks into
    semantic values or other owners' Port contracts.
    """
    root = Path(__file__).resolve().parents[2] / "src" / "legoai"
    asyncio_importers = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(
                alias.name.split(".")[0] == "asyncio" for alias in node.names
            ):
                asyncio_importers.append(path)
            if (
                isinstance(node, ast.ImportFrom)
                and (node.module or "").split(".")[0] == "asyncio"
            ):
                asyncio_importers.append(path)
    module_names = {
        "legoai." + ".".join(path.relative_to(root).with_suffix("").parts)
        for path in asyncio_importers
    }
    assert module_names == {"legoai.reference.execution", "legoai.reference.model"}


def test_execution_values_does_not_import_reference_execution() -> None:
    # Reverse-dependency check: M1's immutable semantic values must never
    # depend on M10's Coordinator (or any reference realization) -- the
    # dependency direction is strictly reference -> values, never the
    # reverse.
    assert "execution-owner" in violations(
        {
            "legoai.execution.values": (
                "from legoai.reference.execution import ExecutionCoordinator"
            )
        }
    )


@pytest.mark.parametrize(
    "owner",
    [
        "governance.values",
        "capabilities.values",
        "evidence.values",
        "plugins.values",
    ],
)
def test_m1_through_m9_semantic_values_do_not_import_coordinator(owner: str) -> None:
    reason_by_owner = {
        "governance.values": "governance-owner",
        "capabilities.values": "capabilities-owner",
        "evidence.values": "evidence-owner",
        "plugins.values": "plugins-owner",
    }
    assert reason_by_owner[owner] in violations(
        {
            f"legoai.{owner}": (
                "from legoai.reference.execution import ExecutionCoordinator"
            )
        }
    )


def test_intelligence_model_values_does_not_import_reference_model() -> None:
    # Same reverse-dependency check as M1's execution.values: this owner's
    # immutable semantic values must never depend on its own reference
    # realization (the Ollama Adapter) or any composition wiring.
    assert "intelligence-owner" in violations(
        {
            "legoai.intelligence.model.values": (
                "from legoai.reference.model import OllamaModelAdapter"
            )
        }
    )


def test_composition_root_never_imports_asyncio_or_threading() -> None:
    # `legoai.runtime._composition` may (Gate-2 M11) wire the Coordinator's
    # own already-async methods by explicit construction/`await` -- that
    # requires no `asyncio` import of its own, since `await`/`async def` are
    # language keywords, not names from the `asyncio` module. It must never
    # itself acquire supervision/threading behavior directly: ADR-015 SS2
    # places all structured-concurrency substrate under `legoai.reference.
    # execution` only (proven confined there by
    # `test_asyncio_confined_to_authorized_reference_execution_module`).
    root = Path(__file__).resolve().parents[2] / "src" / "legoai" / "runtime"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not any(
                    alias.name.split(".")[0] in {"asyncio", "threading"}
                    for alias in node.names
                ), path
            if isinstance(node, ast.ImportFrom):
                module_root = (node.module or "").split(".")[0]
                assert module_root not in {"asyncio", "threading"}, path


@pytest.mark.parametrize(
    "filename", ["governed.py", "model_governed.py", "model_selection.py"]
)
def test_composition_root_does_not_hide_coordinator_behind_generic_lookup(
    filename: str,
) -> None:
    # Gate-2 M11's `governed.py` and v0.1's `model_governed.py` legitimately
    # import `ExecutionCoordinator`/`OllamaModelAdapter` by name to wire an
    # explicit, statically-known capability correspondence (never a
    # `dict[CapabilityId, Callable]`, registry or service-locator pattern)
    # -- this proves no such generic lookup structure, and no
    # dynamic-loading primitive, was introduced instead. AST-based (not
    # substring) so either module's own prose explaining what it
    # deliberately does *not* do cannot trip the check.
    path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "legoai"
        / "runtime"
        / "_composition"
        / filename
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden_names = {
        "ProviderRegistry",
        "ServiceLocator",
        "ImplementationRegistry",
        "eval",
        "exec",
        "compile",
        "__import__",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            assert node.name not in forbidden_names, node.name
        if isinstance(node, ast.Name):
            assert node.id not in forbidden_names, node.id
        if isinstance(node, ast.Attribute):
            assert node.attr not in forbidden_names, node.attr
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = getattr(node, "module", None) or ""
            assert "importlib" not in module, module
            assert not any("importlib" in alias.name for alias in node.names), path
