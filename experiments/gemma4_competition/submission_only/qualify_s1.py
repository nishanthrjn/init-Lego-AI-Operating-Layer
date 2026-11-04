"""S1 E4B operational eligibility; reuse shared receipt reconciliation/generation."""
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent / 'results/dev-16v-comparison.json'
SUBMISSIONS = HERE.parent / 'results/submissions.json'
ZIP_SHA256 = '6f38e73cbd441b9c55a5c04e25d2350fdf1deb3fccbd8b1631fcbee7af4ca36a'
MANIFEST_SHA256 = '219369b4ed0f7e62f28a125c5e6cabac9031012aa41964179ca5c293c92272a0'
MODEL = 'gemma-4-e4b-it-qat-w4a16-ct'


def require_qualification_gate(path=EVIDENCE, submissions=SUBMISSIONS):
    raw = Path(path).read_bytes()
    registry_raw = Path(submissions).read_bytes()
    doc, registry = json.loads(raw), json.loads(registry_raw)
    selection = registry.get('s1_local_selection', {})
    if selection.get('candidate') != 's1' or selection.get('purpose') != 'E4B_BONUS_ENTRY':
        raise ValueError('S1 blocked: explicit E4B_BONUS_ENTRY purpose required')
    run = doc.get('s1_dev16v_attempt1', {})
    if (run.get('candidate') != 's1' or run.get('subset') != 'dev-16v'
            or run.get('state') != 'COMPLETED' or run.get('tasks') != 16
            or run.get('operational_gate') not in ('PASSED', 'PASSED_MAINTAINER_REPORTED')):
        raise ValueError('S1 blocked: completed dev-16v operational pass required')
    if (run.get('zip_sha256') != ZIP_SHA256 or run.get('manifest_sha256') != MANIFEST_SHA256
            or run.get('model_variant') != MODEL):
        raise ValueError('S1 blocked: evaluated E4B package identity required')
    if doc.get('s2_dev16v_attempt1', {}).get('gate') != 'FAILED':
        raise ValueError('S1 blocked: recorded S2 rejection required')
    if type(run.get('harness_errors')) is not int or run['harness_errors'] != 0:
        raise ValueError('S1 blocked: verified harness_errors=0 required (missing is not zero)')
    if run.get('tool_argument_rejection_definition') != 'mandatory input parameters are not present':
        raise ValueError('S1 blocked: exact tool_rejections.py observation-phrase definition required')
    attempted, rejected = run.get('all_tool_attempted'), run.get('all_tool_rejected')
    if (type(attempted) is not int or attempted <= 0 or type(rejected) is not int
            or rejected < 0 or rejected > attempted or rejected / attempted > 0.05):
        raise ValueError('S1 blocked: all-tool rejection counts and rate<=5% required')
    bound = run.get('bootstrap_upper95_hours')
    if type(bound) not in (int, float) or not math.isfinite(bound) or not 0 <= bound <= 10.5:
        raise ValueError('S1 blocked: numeric bootstrap upper95<=10.5 hours required')
    return {'development_gate': 'PASSED', 'qualification_purpose': 'E4B_BONUS_ENTRY',
            'model_variant': MODEL, 'development_evidence_sha256': hashlib.sha256(raw).hexdigest(),
            'selection_evidence_sha256': hashlib.sha256(registry_raw).hexdigest()}


def main():
    from qualify_p3 import main as prepare
    prepare('s1', guard=require_qualification_gate)


if __name__ == '__main__':
    main()
