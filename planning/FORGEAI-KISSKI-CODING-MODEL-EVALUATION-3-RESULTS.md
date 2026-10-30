# FORGEAI-KISSKI-CODING-MODEL-EVALUATION-3 results

## Evidence provenance

Values transcribed from the derived evaluation.json reports in the listed custody folders.

- Manifest: `64f666fef6c576c507d87dc943e1ec2db5fc4388e67971b61352eac37c660bc1`
- Pack: `ed82567ae6f2957f7b0f982e829e8f56c6d0e34978ee431b99d49da75029beaa`
- Phase A custody folder: `kisski-eval-v3-_e47iq4v`
- Phase B custody folder: `kisski-eval-v3-ky6iop0z`

## gemma-4-31b-it

Phase A: **4/4 passed**.

| Phase B task | Repeatability | Reported details |
| --- | --- | --- |
| multi | 2_OF_2 | Passed both repeats. |
| security | 2_OF_2 | Passed both repeats. |
| abstention | 2_OF_2 | Passed both repeats. |
| abstention_heldout | 2_OF_2 | Passed both repeats. |
| review | 2_OF_2 | r1/r2/r3 found; 0 false positives. |
| review_clean | 2_OF_2 | Passed both repeats. |
| review_clean2 | 2_OF_2 | Passed both repeats. |
| review_heldout | 0_OF_2 | Each repeat: 1 true positive, 1 missed critical, 1 false positive. |
| review_heldout2 | 0_OF_2 | Each repeat: 1 true positive, 1 missed critical, 1 false positive. |

Malformed outputs: **0 of 22**.

Classification: **MODEL_NOT_QUALIFIED**. The v3 verdict is **final**.

## Conclusion

The reviewer v1.1.0 category rule fixed the motivating case but did not
generalize to held-out security defects. Prompt tuning against these held-out
tasks stops here. Unattended admission remains blocked.
