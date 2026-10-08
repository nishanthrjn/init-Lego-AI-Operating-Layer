# MODEL-STRUCTURED-OUTPUT-1-LIVE-PROBE PASSED

- Probe: `d54d022d-9928-4f5d-a9b8-8745929e97f5`
- Git HEAD: `d9645d0f05d8beff61ed4fd7febe2f142fcc1b6d`
- Ollama: 0.40.0
- Model: qwen2.5-coder:14b `sha256:9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849`
- Schema digest: `dd522666abf2ef6cb884ab37fb25da4e56f123febc5ee1f7064cbb570aeab4e2`
- Semantic calls: 1
- Elapsed: 100.878 s (bound 600 s)
- Execution: SUCCEEDED / effect COMPLETED
- JSON parse: SUCCESS

| Condition | Result |
| --- | --- |
| exactly one semantic call | yes |
| governed route reached the Ollama adapter | yes |
| loopback endpoint | yes |
| structured requirement sent as format | yes |
| no exception | yes |
| execution SUCCEEDED | yes |
| effect known and COMPLETED | yes |
| Core returned text | yes |
| one parseable JSON document | yes |
| schema A_root_object | yes |
| schema B_exact_declared_properties | yes |
| schema C_no_additional_property | yes |
| schema D_status_in_enum | yes |
| schema E_label_within_max_length | yes |
| schema F_items_within_max_items | yes |
| schema G_items_elements_valid | yes |
| schema H_note_nullable_valid | yes |
| schema I_required_present | yes |

One controlled synthetic call with the exact recorded runtime and model identity. Compatibility evidence only; not statistical reliability, Agent quality, safety, OpenAI-compatible support or production readiness.
