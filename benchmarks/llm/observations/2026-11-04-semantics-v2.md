# Kaggle/Cerune semantics v2 — observation, 2026-11-04 (JST)

## Provenance

Observed directly from Kaggle Notebook screenshots supplied by the experimenter
in the related development conversation, not fetched via the Kaggle API. The
model label was displayed as **`google/gemini-3.8-flash`**. The benchmark was
executed once per condition, with six **public** cases. The Kaggle task was not
independently re-run from this repository.

Reference: [Kaggle semantics v2 script](../semantics_v2/kaggle_semantics_v2.py).
The run did not save a raw machine-readable export to this repository. The
details below are **screenshot transcriptions and derived figures**, not claims
of possession of the underlying model traces.

## Results

| Condition | Strict string equality | Only error-code formatting normalized |
| --- | ---: | ---: |
| No reference (`baseline`) | 4 / 6 (66.7%) | 5 / 6 (83.3%) |
| With Cerune reference (`spec`) | 6 / 6 (100%) | 6 / 6 (100%) |
| Difference | +2 / 6 (+33.3 percentage points) | +1 / 6 (+16.7 points) |

The baseline produced `OK:99,99` for `owned_array_copy`, while the actual
Cerune result is `OK:20,99`. This is a **semantic error** consistent with
mistakenly assuming reference-sharing rather than value copying. The `spec`
condition passed the same case.

The other baseline strict mismatch was `ERROR:INTEGER_OVERFLOW:5` versus the
expected `ERROR:integer-overflow:5`. It correctly recognized the runtime
failure and preserved earlier stdout; its error-code spelling differed.
The narrow score correction handles only known error-code case and underscore
versus hyphen, without changing any stdout or runtime behavior.

The screenshots show overall `RESULT: 1.0` for `spec` and each case as PASS.
The captured baseline responses are:

| Case | Baseline model response | Strict | Normalized |
| --- | --- | --- | --- |
| owned_array_copy | `OK:99,99` | fail | fail |
| iteration_snapshot | `OK:1,2,3,99` | pass | pass |
| utf8_byte_len | `OK:9,3` | pass | pass |
| short_circuit | `OK:false,true` | pass | pass |
| zero_repeat_evaluation | `OK:77,0` | pass | pass |
| checked_overflow | `ERROR:INTEGER_OVERFLOW:5` | fail | pass |

## Interpretation and next experiment

This is a **pilot observation**, not evidence of statistically significant
language acquisition. There are only six published questions, a single model,
and one run per condition; reference content and prompt length differ. The
observation supports a *specific* example of correct in-context adaptation for
Cerune's array-value semantics.

The next phase should ask the LLM to **write** Cerune functions, capture its
raw answers without running them on Kaggle, then compile and grade those
answers with the existing isolated `codegen_eval.py` runner. Do not describe
a static-format check as proof that generated code executes.
