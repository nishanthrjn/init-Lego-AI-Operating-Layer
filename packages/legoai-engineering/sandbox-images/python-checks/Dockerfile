# LegoAI engineering sandbox image: Python engineering checks.
#
# Adds only the M5 check tools (pytest, Ruff, mypy) and their locked
# dependencies to the already-qualified M6 base. No application source,
# secrets, credentials, Git, provider SDKs or runtime installation. Network is
# used only by this operator build step; sandbox runtime stays network=none.
#
# requirements.txt is exported from packages/legoai-engineering/uv.lock:
#   uv export --locked --offline --only-group dev --no-emit-project \
#     --prune hatchling --prune editables --format requirements-txt \
#     --no-header --output-file sandbox-images/python-checks/requirements.txt
#
# The built image is approved only by its exact local image ID after Docker
# qualification (validate_consumer_readiness_cr2a.py). A rebuild produces a new
# ID and requires requalification; bit-for-bit reproducibility is not claimed.

FROM python@sha256:82bc3c539b8813ada9d68c63b40158fa002f7f33de9bf3312a3dfdc0620dff56

COPY requirements.txt /tmp/legoai-python-checks-requirements.txt

RUN python -m pip install \
        --no-cache-dir \
        --no-compile \
        --disable-pip-version-check \
        --no-input \
        --no-deps \
        --only-binary=:all: \
        --require-hashes \
        --requirement /tmp/legoai-python-checks-requirements.txt \
    && python -m pip check \
    && rm /tmp/legoai-python-checks-requirements.txt

LABEL org.legoai.sandbox.image="python-checks" \
      org.legoai.sandbox.base="python@sha256:82bc3c539b8813ada9d68c63b40158fa002f7f33de9bf3312a3dfdc0620dff56"
