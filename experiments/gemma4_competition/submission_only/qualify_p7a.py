"""P7a confirmation guard and shared submission preparation; no import-time execution."""
import hashlib
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EVIDENCE = HERE.parent / 'results/dev-16v-comparison.json'
ZIP_SHA256 = '68f685853161c0a3c0653e6c2a42655f53fc03b9f3ed8702b80c681390ef0c34'
MANIFEST_SHA256 = '2b982fc8bcfd01f60d505b0d41958370b7b617412315d029e002eb9f05f7d7f7'


def require_confirmation_gate(path=EVIDENCE):
    raw = Path(path).read_bytes()
    doc = json.loads(raw)
    decision = doc.get('p7a_confirmation_decision', {})
    if (decision.get('status') != 'PASSED' or decision.get('same_config_verified') is not True
            or doc.get('p7_selection', {}).get('selected_candidate') != 'p7a'):
        raise ValueError('P7A blocked: recorded passing unchanged confirmation required')
    expected_source = hashlib.sha256((HERE.parent / 'local_eval/source-pins.json').read_bytes()).hexdigest()
    def number(value, name, maximum, integer=False):
        if (type(value) not in (int, float) or not math.isfinite(value) or value < 0
                or value > maximum or (integer and type(value) is not int)):
            raise ValueError('P7A blocked: invalid/missing ' + name)
        return value
    solved, locations = [], set()
    for attempt in (1, 2):
        run = doc.get(f'p7a_attempt{attempt}', {})
        if (run.get('candidate') != 'p7a' or run.get('subset') != 'dev-16v'
                or type(run.get('attempt')) is not int or run['attempt'] != attempt
                or run.get('state') != 'COMPLETED' or run.get('verifiable') != 16):
            raise ValueError('P7A blocked: two complete independent dev-16v runs required')
        if (run.get('zip_sha256') != ZIP_SHA256 or run.get('manifest_sha256') != MANIFEST_SHA256
                or run.get('model') != 'gemma-4-31b-it-qat-w4a16-ct'
                or run.get('source_pins_sha256') != expected_source):
            raise ValueError('P7A blocked: unchanged package/model/environment identity required')
        location = run.get('retained_path')
        if not isinstance(location, str) or not location.strip():
            raise ValueError('P7A blocked: retained run path required')
        identity = location.replace(chr(92), '/').rstrip('/').casefold()
        if identity in locations:
            raise ValueError('P7A blocked: confirmation must be independent')
        locations.add(identity)
        solved.append(number(run.get('resolved'), 'resolved', 16, True))
        empty = number(run.get('empty_patches'), 'empty patches', 3, True)
        if solved[-1] + empty > 16:
            raise ValueError('P7A blocked: inconsistent task counts')
        if run.get('bootstrap_method') != 'REPO_ANALYSIS_116_TASK_BOOTSTRAP_V1':
            raise ValueError('P7A blocked: authoritative repo bootstrap required')
        number(run.get('bootstrap_upper95_hours'), 'bootstrap upper95 hours', 11)
    if solved[0] < 11 or sum(solved) / 2 < 10.5:
        raise ValueError('P7A blocked: screening >=11 and confirmed mean >=10.5 required')
    return {'development_gate': 'PASSED', 'development_evidence_sha256': hashlib.sha256(raw).hexdigest()}


SUBMISSIONS = HERE.parent / 'results/submissions.json'


def require_qualification_gate(path=EVIDENCE, submissions=SUBMISSIONS):
    """Separate an explicit pre-score measurement from local adoption eligibility."""
    raw = Path(submissions).read_bytes()
    registry = json.loads(raw)
    amendment = registry.get('p7a_exploratory_authorization')
    if amendment is None:
        return require_confirmation_gate(path)
    expected = {
        'amendment_id': 'P7A-EXPLORATORY-LB-1', 'candidate': 'p7a',
        'purpose': 'EXPLORATORY_LB_MEASUREMENT',
        'status': 'AUTHORIZED_PENDING_QUALIFICATION', 'execution_status': 'NOT_SUBMITTED',
        'local_adoption': 'NOT_ADOPTED', 'local_confirmation': 'FAILED',
        'zip_sha256': ZIP_SHA256, 'experimental_manifest_sha256': MANIFEST_SHA256,
        'zip_size': 7359, 'adopt_public_score_at_least': 0.17,
        'p5_mean_public_score': 0.14, 'otherwise': 'RETAIN_P5',
        'final_selection_rules': 'UNCHANGED',
    }
    if not isinstance(amendment, dict) or any(amendment.get(k) != v for k, v in expected.items()):
        raise ValueError('P7A blocked: exact exploratory amendment required')
    if (amendment.get('recorded_before_any_p7a_public_score') is not True
            or type(amendment.get('maximum_submissions')) is not int or amendment['maximum_submissions'] != 1
            or type(amendment.get('submissions_used')) is not int or amendment['submissions_used'] != 0
            or amendment.get('submission_ids') != [] or amendment.get('public_score') is not None):
        raise ValueError('P7A blocked: unused single pre-score measurement required')
    for run in registry.get('runs', []):
        if run.get('candidate') == 'p7a' and (
                run.get('status') != 'NOT_SUBMITTED' or run.get('public_score') is not None):
            raise ValueError('P7A blocked: exploratory submission already recorded')
    evidence_raw = Path(path).read_bytes()
    evidence = json.loads(evidence_raw)
    decision = evidence.get('p7a_confirmation_decision', {})
    if decision.get('status') != 'FAILED' or decision.get('decision') != 'RETAIN_P5':
        raise ValueError('P7A blocked: failed local adoption record must remain intact')
    for attempt in (1, 2):
        run = evidence.get(f'p7a_attempt{attempt}', {})
        if run.get('zip_sha256') != ZIP_SHA256 or run.get('manifest_sha256') != MANIFEST_SHA256:
            raise ValueError('P7A blocked: exploratory identity differs from evaluated package')
    return {
        'development_gate': 'FAILED', 'local_adoption': 'NOT_ADOPTED',
        'qualification_purpose': 'EXPLORATORY_LB_MEASUREMENT',
        'amendment_id': amendment['amendment_id'], 'maximum_submissions': 1,
        'development_evidence_sha256': hashlib.sha256(evidence_raw).hexdigest(),
        'exploratory_authorization_sha256': hashlib.sha256(raw).hexdigest(),
        'adopt_public_score_at_least': 0.17,
    }

def main():
    from qualify_p3 import main as prepare
    prepare('p7a', guard=require_qualification_gate)


if __name__ == '__main__':
    main()
