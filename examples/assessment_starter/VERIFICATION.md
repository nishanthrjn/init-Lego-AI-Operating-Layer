# Verification

The maintained example and a generated temporary project were both verified.

- Reference backend: 14 tests passed; strict mypy, Ruff lint and formatting passed.
- Exporter: 8 tests passed; strict mypy, Ruff lint and formatting passed.
- Standalone backend: 14 tests passed; strict mypy, Ruff lint and formatting passed.
- Reference and standalone frontends: npm install, build and lint succeeded;
  npm reported zero vulnerabilities.
- Both stacks passed loopback HTTP smoke checks: served Vite page, proxied POST
  to FastAPI, application service, fixed model response, and health endpoint.
  Temporary ports were used because port 8000 was occupied. Servers were stopped.
- Generated source search for `legoai.` returned zero matches. The generated
  service also ran with Python -I -S: no installed platform or site packages.
- Core regression run: 1,508 passed and two SQLite abrupt-termination cases failed.
  Diagnosis showed that the Windows virtual-environment launcher PID differed
  from the interpreter PID, leaving the database-owning child alive after kill.
  Both failing cases then passed using the actual base interpreter with the
  source and existing test dependencies on PYTHONPATH. No Core code or tests
  were changed. The initial failure is retained here, not reported as a clean
  single-run 1,510-test result.

Installed dependencies produced two non-fatal upstream warnings: ESLint 9 is
deprecated, and Starlette recommends httpx2 instead of its current httpx
TestClient integration. These did not prevent the recorded checks.

No live model/provider validation, authenticated deployment, visual browser
interaction test, or Docker qualification is claimed. The example is local and
offline by design. Dependency downloads require network only during installation.
