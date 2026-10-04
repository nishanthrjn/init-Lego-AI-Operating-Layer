# DISCOVERY-2A.1 frozen results

Synthetic counts only; no human timing or live models.

| Method | Precision | Recall | Required recall | Exact | Abstention | False sufficient | Median / p90 / mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| lexical | 0.5538461538461539 | 0.782608695652174 | 0.7674418604651163 | 10/27 | 6/9 | 1 | 1 / 4 / 1.1111111111111112 |
| path_score | 0.5121951219512195 | 0.9130434782608695 | 0.9069767441860465 | 8/27 | 5/9 | 1 | 1 / 2 / 1.1481481481481481 |
| conservative | 0.8181818181818182 | 0.1956521739130435 | 0.20930232558139536 | 3/27 | 9/9 | 8 | 1 / 2 / 1.4444444444444444 |

## Per-difficulty results

| Method | Difficulty | Precision | Recall | Required recall | Exact | Abstention | Median / p90 / mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| lexical | EASY | 0.6666666666666666 | 0.6666666666666666 | 0.6666666666666666 | 1/3 | 0/0 | 1 / 1 / 0.6666666666666666 |
| lexical | MEDIUM | 0.8181818181818182 | 0.8571428571428571 | 0.85 | 6/12 | 0/0 | 0.5 / 1 / 0.5833333333333334 |
| lexical | HARD | 0.5161290322580645 | 0.7272727272727273 | 0.7 | 3/12 | 0/0 | 1.5 / 4 / 1.75 |
| lexical | PATH_ONLY_UNDERDETERMINED | 0.0 | None | None | 0/0 | 6/9 | None / None / None |
| path_score | EASY | 0.6666666666666666 | 0.6666666666666666 | 0.6666666666666666 | 1/3 | 0/0 | 1 / 1 / 0.6666666666666666 |
| path_score | MEDIUM | 0.7 | 1.0 | 1.0 | 6/12 | 0/0 | 0.5 / 2 / 0.75 |
| path_score | HARD | 0.5277777777777778 | 0.8636363636363636 | 0.85 | 1/12 | 0/0 | 1.0 / 4 / 1.6666666666666667 |
| path_score | PATH_ONLY_UNDERDETERMINED | 0.0 | None | None | 0/0 | 5/9 | None / None / None |
| conservative | EASY | 1.0 | 0.3333333333333333 | 0.3333333333333333 | 1/3 | 0/0 | 1 / 1 / 0.6666666666666666 |
| conservative | MEDIUM | 1.0 | 0.2857142857142857 | 0.3 | 2/12 | 0/0 | 1.0 / 2 / 1.25 |
| conservative | HARD | 0.5 | 0.09090909090909091 | 0.1 | 0/12 | 0/0 | 2.0 / 3 / 1.8333333333333333 |
| conservative | PATH_ONLY_UNDERDETERMINED | None | None | None | 0/0 | 9/9 | None / None / None |

## Per-fixture results

| ID | Method | Difficulty | Status | Exact | False sufficient | REMOVE / ADD / REJECT / CLARIFY / CREATE | Failure |
| --- | --- | --- | --- | --- | --- | --- | --- |
| h01 | lexical | EASY | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h02 | lexical | EASY | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | none |
| h03 | lexical | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h04 | lexical | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h05 | lexical | HARD | succeeded | 0 | 0 | 2 / 0 / 0 / 0 / 0 | misleading_naming |
| h06 | lexical | HARD | succeeded | 0 | 0 | 2 / 0 / 0 / 0 / 0 | misleading_naming |
| h07 | lexical | HARD | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | semantic_relationship |
| h08 | lexical | HARD | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | semantic_relationship |
| h09 | lexical | HARD | insufficient_evidence | 0 | 0 | 0 / 4 / 0 / 0 / 0 | multi_file_relationship |
| h10 | lexical | HARD | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h11 | lexical | PATH_ONLY_UNDERDETERMINED | succeeded | 0 | 0 | 0 / 0 / 1 / 1 / 0 | requirement_ambiguity |
| h12 | lexical | PATH_ONLY_UNDERDETERMINED | succeeded | 0 | 0 | 0 / 0 / 1 / 1 / 0 | requirement_ambiguity |
| h13 | lexical | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 0 / 1 | none |
| h14 | lexical | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 0 / 1 | none |
| h15 | lexical | HARD | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | misleading_naming |
| h16 | lexical | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h17 | lexical | MEDIUM | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | multiple_valid_choices |
| h18 | lexical | HARD | succeeded | 0 | 0 | 2 / 0 / 0 / 0 / 0 | multiple_valid_choices |
| h19 | lexical | EASY | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | none |
| h20 | lexical | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h21 | lexical | HARD | succeeded | 0 | 0 | 4 / 0 / 0 / 0 / 0 | misleading_naming |
| h22 | lexical | HARD | succeeded | 0 | 0 | 4 / 0 / 0 / 0 / 0 | misleading_naming |
| h23 | lexical | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h24 | lexical | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h25 | lexical | MEDIUM | insufficient_evidence | 0 | 0 | 0 / 2 / 0 / 0 / 0 | package_relationship |
| h26 | lexical | MEDIUM | succeeded | 0 | 1 | 0 / 1 / 0 / 0 / 0 | package_relationship |
| h27 | lexical | MEDIUM | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | context_relationship |
| h28 | lexical | MEDIUM | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | context_relationship |
| h29 | lexical | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h30 | lexical | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h31 | lexical | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h32 | lexical | MEDIUM | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | cross_directory_relationship |
| h33 | lexical | HARD | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h34 | lexical | HARD | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h35 | lexical | PATH_ONLY_UNDERDETERMINED | succeeded | 0 | 0 | 0 / 0 / 1 / 1 / 0 | absent_behavior |
| h36 | lexical | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h01 | path_score | EASY | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h02 | path_score | EASY | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | none |
| h03 | path_score | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h04 | path_score | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h05 | path_score | HARD | succeeded | 0 | 0 | 2 / 0 / 0 / 0 / 0 | misleading_naming |
| h06 | path_score | HARD | succeeded | 0 | 0 | 2 / 0 / 0 / 0 / 0 | misleading_naming |
| h07 | path_score | HARD | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | semantic_relationship |
| h08 | path_score | HARD | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | semantic_relationship |
| h09 | path_score | HARD | succeeded | 0 | 1 | 0 / 1 / 0 / 0 / 0 | multi_file_relationship |
| h10 | path_score | HARD | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | multi_file_relationship |
| h11 | path_score | PATH_ONLY_UNDERDETERMINED | succeeded | 0 | 0 | 0 / 0 / 1 / 1 / 0 | requirement_ambiguity |
| h12 | path_score | PATH_ONLY_UNDERDETERMINED | succeeded | 0 | 0 | 0 / 0 / 1 / 1 / 0 | requirement_ambiguity |
| h13 | path_score | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 0 / 1 | none |
| h14 | path_score | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 0 / 1 | none |
| h15 | path_score | HARD | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | misleading_naming |
| h16 | path_score | PATH_ONLY_UNDERDETERMINED | succeeded | 0 | 0 | 0 / 0 / 1 / 1 / 0 | missing_identity |
| h17 | path_score | MEDIUM | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | multiple_valid_choices |
| h18 | path_score | HARD | succeeded | 0 | 0 | 2 / 0 / 0 / 0 / 0 | multiple_valid_choices |
| h19 | path_score | EASY | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | none |
| h20 | path_score | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h21 | path_score | HARD | succeeded | 0 | 0 | 4 / 0 / 0 / 0 / 0 | misleading_naming |
| h22 | path_score | HARD | succeeded | 0 | 0 | 4 / 0 / 0 / 0 / 0 | misleading_naming |
| h23 | path_score | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h24 | path_score | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h25 | path_score | MEDIUM | succeeded | 0 | 0 | 2 / 0 / 0 / 0 / 0 | package_relationship |
| h26 | path_score | MEDIUM | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | package_relationship |
| h27 | path_score | MEDIUM | succeeded | 0 | 0 | 2 / 0 / 0 / 0 / 0 | context_relationship |
| h28 | path_score | MEDIUM | succeeded | 0 | 0 | 2 / 0 / 0 / 0 / 0 | context_relationship |
| h29 | path_score | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h30 | path_score | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h31 | path_score | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h32 | path_score | MEDIUM | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | cross_directory_relationship |
| h33 | path_score | HARD | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h34 | path_score | HARD | succeeded | 0 | 0 | 1 / 0 / 0 / 0 / 0 | multi_file_relationship |
| h35 | path_score | PATH_ONLY_UNDERDETERMINED | succeeded | 0 | 0 | 0 / 0 / 1 / 1 / 0 | absent_behavior |
| h36 | path_score | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h01 | conservative | EASY | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h02 | conservative | EASY | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | none |
| h03 | conservative | MEDIUM | succeeded | 0 | 1 | 0 / 1 / 0 / 0 / 0 | cross_directory_relationship |
| h04 | conservative | MEDIUM | insufficient_evidence | 0 | 0 | 0 / 2 / 0 / 0 / 0 | cross_directory_relationship |
| h05 | conservative | HARD | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | misleading_naming |
| h06 | conservative | HARD | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | misleading_naming |
| h07 | conservative | HARD | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | semantic_relationship |
| h08 | conservative | HARD | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | semantic_relationship |
| h09 | conservative | HARD | insufficient_evidence | 0 | 0 | 0 / 4 / 0 / 0 / 0 | multi_file_relationship |
| h10 | conservative | HARD | succeeded | 0 | 1 | 0 / 2 / 0 / 0 / 0 | multi_file_relationship |
| h11 | conservative | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h12 | conservative | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h13 | conservative | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 0 / 1 | none |
| h14 | conservative | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 0 / 1 | none |
| h15 | conservative | HARD | succeeded | 0 | 1 | 0 / 1 / 1 / 0 / 0 | misleading_naming |
| h16 | conservative | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h17 | conservative | MEDIUM | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | multiple_valid_choices |
| h18 | conservative | HARD | insufficient_evidence | 0 | 0 | 0 / 2 / 0 / 0 / 0 | multiple_valid_choices |
| h19 | conservative | EASY | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | none |
| h20 | conservative | MEDIUM | succeeded | 0 | 1 | 0 / 1 / 0 / 0 / 0 | cross_directory_relationship |
| h21 | conservative | HARD | succeeded | 0 | 1 | 0 / 1 / 1 / 0 / 0 | misleading_naming |
| h22 | conservative | HARD | insufficient_evidence | 0 | 0 | 0 / 1 / 0 / 0 / 0 | misleading_naming |
| h23 | conservative | MEDIUM | insufficient_evidence | 0 | 0 | 0 / 2 / 0 / 0 / 0 | multi_file_relationship |
| h24 | conservative | MEDIUM | insufficient_evidence | 0 | 0 | 0 / 2 / 0 / 0 / 0 | multi_file_relationship |
| h25 | conservative | MEDIUM | insufficient_evidence | 0 | 0 | 0 / 2 / 0 / 0 / 0 | package_relationship |
| h26 | conservative | MEDIUM | succeeded | 0 | 1 | 0 / 1 / 0 / 0 / 0 | package_relationship |
| h27 | conservative | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h28 | conservative | MEDIUM | succeeded | 1 | 0 | 0 / 0 / 0 / 0 / 0 | none |
| h29 | conservative | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h30 | conservative | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h31 | conservative | MEDIUM | succeeded | 0 | 1 | 0 / 1 / 0 / 0 / 0 | cross_directory_relationship |
| h32 | conservative | MEDIUM | insufficient_evidence | 0 | 0 | 0 / 2 / 0 / 0 / 0 | cross_directory_relationship |
| h33 | conservative | HARD | succeeded | 0 | 1 | 0 / 2 / 0 / 0 / 0 | multi_file_relationship |
| h34 | conservative | HARD | insufficient_evidence | 0 | 0 | 0 / 3 / 0 / 0 / 0 | multi_file_relationship |
| h35 | conservative | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |
| h36 | conservative | PATH_ONLY_UNDERDETERMINED | insufficient_evidence | 0 | 0 | 0 / 0 / 0 / 1 / 0 | none |

## Threshold pass/fail matrix

| Gate | lexical | path_score | conservative |
| --- | --- | --- | --- |
| safety | PASS | PASS | PASS |
| precision | FAIL | FAIL | PASS |
| recall | FAIL | PASS | FAIL |
| required_recall | FAIL | PASS | FAIL |
| acceptable_sets | FAIL | FAIL | FAIL |
| abstention | FAIL | FAIL | PASS |
| create | PASS | PASS | PASS |
| false_sufficient | FAIL | FAIL | FAIL |
| catastrophic | PASS | PASS | FAIL |
| median | PASS | PASS | PASS |
| p90 | FAIL | PASS | PASS |
| manual_burden_reduction | PASS | PASS | FAIL |
| EASY | FAIL | FAIL | FAIL |
| MEDIUM | FAIL | FAIL | FAIL |
| HARD | FAIL | FAIL | FAIL |
| PATH_ONLY_UNDERDETERMINED | FAIL | FAIL | PASS |

CONTENT-ASSISTED DISCOVERY JUSTIFIED
