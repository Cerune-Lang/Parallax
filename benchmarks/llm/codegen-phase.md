# Code-generation phase (Kaggle → isolated Cerune execution)

Unlike output prediction, a generation benchmark asks a model to write Cerune
code. A model response **is untrusted source code**, so the Kaggle notebook
only collects the answer — it must never run arbitrary code.

1. Open [kaggle_codegen_collect.py](kaggle_codegen_collect.py). Copy its entire
   content into a new Kaggle code cell and run **that cell only**.
2. It makes **six model requests**: `abs`, `clamp`, `sum_squares`, each with
   `baseline` and `spec`. The output goes to
   `/kaggle/working/cerune_codegen_answers.json`.
3. Download the JSON via Kaggle's Output files. Keep it as an immutable record
   of the raw answers. The notebook prints `CAPTURED`, not a correctness score.
4. On a **separate ephemeral container** with Cerune built, use:
   
   ```sh
   python3 benchmarks/llm/grade_codegen_bundle.py \
     --responses cerune_codegen_answers.json \
     --binary /absolute/path/to/cerune \
     --allow-execution \
     --out cerune_codegen_scores.json
   ```
   
   **Safety:** Container must be isolated from the host and secrets, run as a
   nonroot user, with network disabled and CPU/memory/PID caps. The
   `--allow-execution` flag is not a sandbox. Do not run this on Kaggle, your
   desktop, or any machine containing private data.

The grader runs `cerune check` and `cerune run` against fixed test cases
from [codegen_eval.py](codegen_eval.py). The score bundle reports both
all-tests-passed per task and individual test-case accuracy. **Neither a
syntactic regex match nor a model self-report counts as a passing test**.

This is an exploratory pilot, with public tasks and tests, not a blinded
scientific evaluation. A user-run Kaggle model is not contacted automatically
by GitHub CI. To improve reproducibility, save the exact model/version,
parameters and Cerune commit SHA alongside the raw answer bundle, and
eventually separate public training examples from nonpublic test oracles.
