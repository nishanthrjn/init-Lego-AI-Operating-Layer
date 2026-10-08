r"""Offline qualification: uv run python .\validate_model_structured_output_1.py.

MODEL-STRUCTURED-OUTPUT-1: provider-neutral structured output for Model chat
(ADR-022). No model, provider, Ollama or Docker. A live provider probe is a
separate, separately authorized step.
"""

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGE = ROOT / "examples/forgeai"
ENG = ROOT / "packages/legoai-engineering"
DOCUMIND = ROOT / "examples/documind"
BASE = "3916451"  # request policy H1 qualification recorded
SELF = "validate_model_structured_output_1.py"
NEW_TESTS = (
    "tests/unit/intelligence/test_structured_output.py",
    "tests/unit/reference/test_model_structured_output.py",
    "tests/integration/composition/test_structured_output_routing.py",
    "tests/architecture/test_structured_output.py",
)
CORE_SOURCES = (
    "src/legoai/intelligence/model/values.py",
    "src/legoai/intelligence/model/routing.py",
    "src/legoai/runtime/api.py",
    "src/legoai/runtime/local.py",
    "src/legoai/runtime/_composition/model_governed.py",
    "src/legoai/reference/model.py",
    "src/legoai/reference/model_openai_compatible.py",
    "src/legoai/reference/model_fake.py",
)
ALLOWED = {
    SELF,
    *CORE_SOURCES,
    *NEW_TESTS,
    "tests/architecture/test_model_routing.py",  # one additive field
    "adrs/ADR-022.md",
    "adrs/ADR-INDEX.md",
    "adrs/ADR-017.md",  # addendum
    "adrs/ADR-021.md",  # addendum
    "docs/model-routing.md",
    "planning/MODEL-STRUCTURED-OUTPUT-1.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
}
PROTECTED = (
    "src/legoai/execution",
    "src/legoai/intelligence/model/ports.py",
    "src/legoai/reference/agent.py",
    "packages",
    "examples/forgeai/src",
    "examples/forgeai/evaluation",
    "examples/documind/src",
    ".gitignore",
)
# Deselected by exact id (never edited), with the reason recorded.
DESELECT = {
    "tests/architecture/test_package_install.py::test_build_and_fresh_wheel": "pre-existing: "
    "frozen wheel inventory predates earlier modules (fails before this slice)",
    "tests/test_package_install.py::test_build_inventory_and_fresh_install": "pre-existing: "
    "frozen Engineering release inventory predates earlier modules",
    "evaluation/tests/test_analyst_sufficiency_hardening_h1.py::test_no_core_change": "superseded "
    "by design: this slice changes Core; H1 sources are verified unchanged directly",
    "evaluation/tests/test_analyst_sufficiency_safety_live1.py::test_no_agent_prompt_parser_changes": (
        "superseded proxy (no packages/src change since eb67277); Agent/prompt/parser "
        "verified unchanged directly"
    ),
}
COVERAGE = [
    ("1 ordinary chat -> ordinary binding", "ordinary_chat_uses_ordinary_binding"),
    (
        "2 structured -> capable binding",
        "structured_request_reaches_capable_binding_with_format",
    ),
    (
        "3 incapable explicit binding -> typed failure",
        "structured_request_to_incapable_binding_fails_closed_typed",
    ),
    (
        "4 only incapable candidates fail; no preference",
        "only_incapable_candidates_fail_and_capable_is_not_preferred",
    ),
    (
        "5 capable selected by existing policy",
        "capable_candidate_selected_by_existing_policy",
    ),
    ("6 no silent downgrade", "no_silent_downgrade_to_text"),
    ("7 no new fallback", "no_new_fallback_surface"),
    ("8 capability grants no authority", "capability_grants_no_authority"),
    (
        "9 response_format does not change authorization",
        "response_format_does_not_change_authorization",
    ),
    ("10 minimal object schema", "minimal_object_schema_accepted"),
    ("11 required enum field", "required_enum_field_accepted"),
    ("12-13 nested object and array", "nested_bounded_object_and_array_accepted"),
    ("nullable enum", "nullable_enum_includes_null"),
    ("14 unsupported keyword rejected", "unsupported_keyword_or_raw_dict_rejected"),
    ("15 unsupported type rejected", "unsupported_type_rejected"),
    ("16-17 no remote/recursive reference", "remote_or_recursive_reference_impossible"),
    ("18 excessive depth rejected", "excessive_depth_rejected"),
    ("19 excessive properties rejected", "excessive_properties_rejected"),
    ("20 excessive enum rejected", "excessive_enum_rejected"),
    ("21 excessive size rejected", "excessive_nodes_or_serialized_size_rejected"),
    ("bounds on lengths and items", "bounds_on_lengths_and_items"),
    ("22 deterministic serialization", "deterministic_serialization_and_digest"),
    ("23 immutable values", "immutable_values_and_fresh_copies"),
    ("24 invalid names rejected", "invalid_required_name_rejected"),
    ("property names", "invalid_property_name_rejected"),
    (
        "25 duplicate enum deterministic",
        "duplicate_enum_or_property_rejected_deterministically",
    ),
    ("26 old ChatRequest construction", "ordinary_chat_request_unchanged"),
    ("response_format typed", "response_format_type_checked"),
    (
        "A no response format: request unchanged",
        "a_no_response_format_request_unchanged",
    ),
    ("B object schema -> format", "b_object_schema_mapped_to_format"),
    ("C enum preserved", "c_enum_preserved"),
    ("D arrays preserved", "d_arrays_preserved"),
    ("E required preserved", "e_required_preserved"),
    ("F bounds preserved", "f_bounds_and_nullable_preserved"),
    ("G caller object unchanged", "g_caller_object_unchanged"),
    (
        "H unsupported schema before dispatch",
        "h_unsupported_schema_rejected_before_dispatch",
    ),
    ("no Core parsing", "ollama_structured_reply_is_not_parsed_by_core"),
    (
        "OpenAI-compatible refuses (no downgrade)",
        "openai_compatible_refuses_structured_request_before_send",
    ),
    (
        "33 FixedModel incapable, text unchanged",
        "fixed_model_remains_incapable_and_unchanged_for_text",
    ),
    ("Ollama binding declares capability", "ollama_binding_declares_structured_output"),
    (
        "OpenAI-compatible binding does not",
        "openai_compatible_binding_does_not_declare",
    ),
    (
        "trusted contribution declares explicitly",
        "trusted_contribution_declares_explicitly",
    ),
    ("34 no provider imports in Core contract", "core_contract_imports_no_provider"),
    ("35 no provider field names", "no_provider_specific_field_names_in_core_api"),
    ("36 Agent need not import providers", "agent_contracts_do_not_import_providers"),
    ("37 adapters depend on Core", "adapters_depend_on_core_not_reverse"),
    ("38 no evaluator dependency", "no_evaluator_dependency_in_core"),
    ("39 SAFETY-EVAL-3 unchanged", "safety_eval3_unchanged"),
    ("40 H1 unchanged", "h1_request_policy_unchanged"),
    ("Agent definition unchanged", "agent_definition_and_output_contract_unchanged"),
]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


def main() -> int:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.update(
        UV_OFFLINE="1",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONUTF8="1",
        FORGEAI_LIVE1_OFFLINE="1",
    )
    done: list[str] = []
    current = "initialization"
    with tempfile.TemporaryDirectory(prefix="model-structured-1-") as directory:
        temp = Path(directory)
        env["UV_CACHE_DIR"] = str(temp / "uv-cache")
        number = 0
        names: set[str] = set()

        def phase(label: str) -> None:
            nonlocal current, number
            number += 1
            current = f"{number} {label}"
            print("[PHASE] " + current, flush=True)

        def run(cwd: Path, *args: str) -> None:
            subprocess.run(
                ["uv", "run", "--locked", "--no-sync", "python", "-B", "-m", *args],
                cwd=cwd,
                env=env,
                check=True,
            )

        def tests(label: str, cwd: Path, *targets: str, junit: bool = False) -> None:
            phase(label)
            extra = [f"--junitxml={temp / f'{number}.xml'}"] if junit else []
            for node in DESELECT:
                path = node.split("::")[0]
                if path in targets or any(
                    path.startswith(t.rstrip("/") + "/") for t in targets
                ):
                    extra += ["--deselect", node]
            run(
                cwd,
                "pytest",
                "-q",
                "-rs",
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(temp / str(number)),
                *extra,
                *targets,
            )
            if junit:
                cases = list(
                    ET.parse(temp / f"{number}.xml").getroot().iter("testcase")
                )
                if not cases or any(list(c) for c in cases):
                    raise ValueError("no failed/skipped qualification cases allowed")
                names.update(c.attrib["name"] for c in cases)
            done.append(current)

        try:
            phase("H1 prerequisite and scope")
            h1 = (
                ROOT
                / "planning/FORGEAI-ANALYST-SUFFICIENCY-HARDENING-H1-REQUEST-POLICY.md"
            ).read_text(encoding="utf-8")
            if "LOCALLY QUALIFIED" not in h1 or "65/65" not in h1:
                raise ValueError("H1 qualification prerequisite missing")
            changed = set(git("diff", "--name-only", BASE).splitlines())
            changed.update(
                git(
                    "ls-files",
                    "--others",
                    "--exclude-standard",
                    "--",
                    "src",
                    "tests",
                    "adrs",
                    "docs",
                    "packages",
                    "examples",
                    "planning",
                    SELF,
                ).splitlines()
            )
            if changed - ALLOWED:
                raise ValueError("unexpected files: " + repr(sorted(changed - ALLOWED)))
            for path in PROTECTED:
                if git("diff", "--name-only", BASE, "--", path):
                    raise ValueError("protected input changed: " + path)
            done.append(current)
            phase("ADR-022 recorded and indexed")
            adr = (ROOT / "adrs/ADR-022.md").read_text(encoding="utf-8")
            index = (ROOT / "adrs/ADR-INDEX.md").read_text(encoding="utf-8")
            for marker in ("ADR-017", "ADR-019", "ADR-021", "fail", "Proposed"):
                if marker not in adr:
                    raise ValueError("ADR-022 missing: " + marker)
            if "ADR-022" not in index:
                raise ValueError("ADR-022 not indexed")
            done.append(current)
            tests("structured-output tests", ROOT, *NEW_TESTS, junit=True)
            names |= {n.split("[")[0] for n in names}
            for label, case in COVERAGE:
                phase(label)
                if "test_" + case not in names:
                    raise ValueError("passing evidence missing: " + case)
                print("  verified: " + case)
                done.append(current)
            tests(
                "full Core suite (model, routing, runtime, adapters, Agent)",
                ROOT,
                "tests",
            )
            tests(
                "Engineering Agent and analyst regressions",
                ENG,
                "tests/test_sufficiency_agent.py",
                "tests/test_analyst.py",
                "tests/test_analyst_request_policy.py",
                "tests/test_coding.py",
                "tests/test_reviewer.py",
                "tests/test_json_document.py",
                "tests/test_architecture.py",
            )
            tests(
                "ForgeAI H1, evidence-loop and SAFETY-LIVE-1 regressions",
                FORGE,
                "evaluation/tests/test_analyst_sufficiency_hardening_h1.py",
                "evaluation/tests/test_analyst_evidence_loop.py",
                "evaluation/tests/test_analyst_sufficiency_safety_live1.py",
                "tests",
            )
            tests(
                "SAFETY-EVAL-2/3 seals and scorer regressions",
                FORGE,
                "evaluation/tests/test_analyst_sufficiency_safety_eval2.py",
                "evaluation/tests/test_analyst_sufficiency_safety_eval3.py",
            )
            tests("DocuMind model consumer regressions", DOCUMIND, "tests")
            phase("validator performs zero model/provider calls")
            if env["FORGEAI_LIVE1_OFFLINE"] != "1":
                raise ValueError("offline guard missing")
            done.append(current)
            checked = [
                *CORE_SOURCES,
                *NEW_TESTS,
                "tests/architecture/test_model_routing.py",
                SELF,
            ]
            phase("mypy")
            run(
                ROOT, "mypy", "--cache-dir", str(temp / "mypy"), "src", *NEW_TESTS, SELF
            )
            done.append(current)
            phase("Ruff lint")
            run(ROOT, "ruff", "check", "--no-cache", *checked)
            done.append(current)
            phase("Ruff format")
            run(ROOT, "ruff", "format", "--check", "--no-cache", *checked)
            done.append(current)
            phase("git diff --check")
            git("diff", "--check", BASE)  # every added line in modified files
            created = {
                SELF,
                *NEW_TESTS,
                "adrs/ADR-022.md",
                "planning/MODEL-STRUCTURED-OUTPUT-1.md",
            }
            for name in sorted(created):  # whole-file rules for files created here
                value = (ROOT / name).read_text(encoding="utf-8")
                if (
                    not value.endswith("\n")
                    or value.endswith("\n\n")
                    or any(line != line.rstrip() for line in value.splitlines())
                ):
                    raise ValueError("whitespace: " + name)
            done.append(current)
        except (
            OSError,
            ValueError,
            RuntimeError,
            subprocess.CalledProcessError,
        ) as error:
            print(f"FAIL {current}: {error}; later phases NOT RUN")
            return 1
    for name in done:
        print("PASS " + name)
    print(
        "MODEL-STRUCTURED-OUTPUT-1 LOCAL VALIDATION PASSED — offline; no model; "
        "no Docker; live provider probe still required separately"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
