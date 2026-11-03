# Cerune semantics v2 — Kaggle pilot

The original 3 simple problems scored 3/3 with and without a reference.
This new pilot uses six language semantics cases grounded in Cerune's actual docs.

Run: copy [kaggle_semantics_v2.py](kaggle_semantics_v2.py) to a **new cell** in the Kaggle notebook already used for the first pilot and execute that cell alone.
It calls each of six questions twice: one condition without a language reference, and another with the actual Cerune rules. Compare each `RESULT` to quantify the improvement. Both are public pilot tasks, not blinded holdouts.

| Case | Expected answer | Purpose |
| --- | --- | --- |
| owned_array_copy | `OK:20,99` | See the corresponding `.ceru` and `.json` oracle |
| iteration_snapshot | `OK:1,2,3,99` | See the corresponding `.ceru` and `.json` oracle |
| utf8_byte_len | `OK:9,3` | See the corresponding `.ceru` and `.json` oracle |
| short_circuit | `OK:false,true` | See the corresponding `.ceru` and `.json` oracle |
| zero_repeat_evaluation | `OK:77,0` | See the corresponding `.ceru` and `.json` oracle |
| checked_overflow | `ERROR:integer-overflow:5` | See the corresponding `.ceru` and `.json` oracle |

Each `.ceru` test has a Parallax success or runtime-v1 diagnostic oracle, tested by Cerune `run`, `run-mir`, and `run-vm` in CI. These are six publicly visible questions, so do not infer generalization from this small sample. The variants also differ in prompt length. No generated code is executed in Kaggle. **The .run() calls use model quota.**

The task definitions can be used in one notebook for experimentation; when publishing a single Kaggle Task, select the task intended for publication. If an existing Task shows Stale, it relates to its build snapshot rather than whether the console scores succeeded.
