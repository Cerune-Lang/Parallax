"""Collect model-generated Cerune functions in a Kaggle notebook.

This script DOES NOT compile or execute any model-generated code.
Download /kaggle/working/cerune_codegen_answers.json afterward and grade
in a disposable, network-disabled container with codegen_eval.py.

Each request is a separate conversation. 3 tasks x 2 conditions = 6 calls.
"""
import json
from pathlib import Path
import kaggle_benchmarks as kbench

kbench.config.enable_console_mode(quiet=False, color=None)

# These are exactly the same public prompts as the local codegen evaluator.
# Do not embed the private test input set in the model prompt.
CODEGEN_SPEC = """Cerune is a typed language. Functions: fn solve(x: i64) -> i64 { return x; }
Local variable: value: i64 = 0; Mutable: mut total: i64 = 0;
Assign using total = total + 1;. Expressions: + - * / %, comparisons, && ||.
Control flow: if x > 0 { return 1; } else { return 0; }
While loop: while x > 0 { x = x - 1; }
For loop: for (mut i: i64 = 0; i < 3; i = i + 1) { ... }
Return type is mandatory, statement terminator is ;, blocks use { }.
The calling program is provided separately. Do NOT write main or print.
"""
CODEGEN_REQUESTS = {
    "abs": "Return the nonnegative absolute value of x. Inputs are in [-10000,10000].",
    "clamp": "Return x restricted to the inclusive range 0..100.",
    "sum_squares": ("For x >= 0, return the sum of i*i for i from 1 through x "
                    "inclusive. For x < 0 return 0. Test inputs are small."),
}


def codegen_prompt(task, condition):
    prompt = (
        "Write a complete Cerune function with this exact signature: "
        "fn solve(x: i64) -> i64.\n"
        "No top-level statements, imports, main, or print. Output only Cerune code.\n"
    )
    if condition == "spec":
        prompt += "Language reference:\n" + CODEGEN_SPEC + "\n"
    return prompt + "Task: " + CODEGEN_REQUESTS[task] + "\n"


@kbench.task(name="cerune-codegen-capture-v1")
def collect_code_generation(llm) -> bool:
    records = []
    for condition in ("baseline", "spec"):
        for task in ("abs", "clamp", "sum_squares"):
            # The same model is used for all six fresh conversations.
            with kbench.chats.new(f"cerune-codegen-v1-{condition}-{task}"):
                response = llm.prompt(codegen_prompt(task, condition))
            raw = str(response)
            records.append({
                "task": task,
                "condition": condition,
                "response": raw,
                "prompt": codegen_prompt(task, condition),
            })
            print(f"CAPTURED {condition}/{task}: {len(raw)} characters (not graded)")
    out = Path("/kaggle/working/cerune_codegen_answers.json")
    out.write_text(json.dumps({
        "experiment": "cerune-codegen-v1",
        "status": "captured-not-graded",
        "model": "check console or notebook model selector",
        "records": records,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(records)} model responses to {out}")
    print("Collection completed; this task does not assess correctness.")
    return True


# .run() produces Kaggle's task run record; the JSON above holds raw answers.
collect_code_generation.run(llm=kbench.llm)
