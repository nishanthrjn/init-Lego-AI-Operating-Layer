# Document parsing capability — live verification evidence

Design-time verification artifacts only. **Not production code, not a test suite, not part of `legoai-document` or any DocuMind repository.** These support `../DOCUMENT-PARSING-CAPABILITY-DESIGN.md`'s VERIFIED findings with reproducible, captured evidence rather than documentation-only claims.

## Contents

- `fixtures/` — 16 tiny, synthetic, non-private fixtures (no customer/DocuMind documents).
- `py/generate_fixtures.py` — regenerates every fixture deterministically (uses `pypdf`, `reportlab`, `pillow` — dev-only tools, not `legoai-document` dependencies).
- `py/verify_pypdf.py` — characterizes `pypdf` 6.19.0's actual behavior (exceptions, page/text shape, encryption handling) against the fixtures.
- `dotnet-sk/Verify/`, `dotnet-maf/Verify/` — throwaway console apps that project-reference `DocuMind-SK`'s and `DocuMind-AgentFramework`'s `DocuMind.Core`/`DocuMind.Domain` projects **read-only**, to observe the actual runtime behavior of their parsers against the same fixtures. Neither DocuMind repository was modified.
- `results-pypdf.txt`, `results-sk.txt`, `results-maf.txt` — captured stdout from the runs that produced this batch's VERIFIED findings.

## Reproducing

```sh
# Python / pypdf
cd py
uv venv --python 3.14 .venv
uv pip install --python .venv pypdf reportlab pillow
.venv/Scripts/python.exe generate_fixtures.py
.venv/Scripts/python.exe verify_pypdf.py

# SK parser
cd ../dotnet-sk/Verify
dotnet run

# MAF parser
cd ../../dotnet-maf/Verify
dotnet run
```

`.venv/`, `bin/`, and `obj/` are gitignored and were removed after capturing `results-*.txt` — they are fully regenerable via the commands above and are not needed to read the captured evidence.

## Scope note on the MAF OCR path

`dotnet-maf/Verify/Program.cs` stubs `IVisionExtractionService` with an offline, canned response (`StubVisionExtractionService`) purely to confirm *whether the OCR fallback branch is reached* for a given fixture. **No real model/network call was made.** OCR output content/quality is explicitly out of scope for `document.parsing` v1 (see the design document §14) and was not characterized.
