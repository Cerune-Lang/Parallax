"""Kaggle Community Benchmarks pilot: Cerune output prediction.

No generated code is executed in this task. Three independent conditions use
the same cases and model; each case is evaluated in a fresh chat context.
See README.md for study limitations (public cases, small N, no blinded holdout).
"""
import kaggle_benchmarks as kbench

# Avoid Jupyter Bokeh/Panel widgets failing to render on Kaggle mobile/browser.
kbench.config.enable_console_mode(quiet=False, color=None)

SPEC = """Cerune is a typed programming language.
Variables: a: i64 = 7; / mut a: i64 = 7; (mutable variables may be reassigned).
Statements end with ;. print(expr); prints a value followed by a newline.
Integer types include i64; integer division truncates toward zero.
Arrays: a: [i64; 3] = [2, 4, 6]; index with a[0], length with array_len(a).
For loop: for (mut i: i64 = 0; i < 3; i = i + 1) { ... }
While loop: while condition { ... }
Conditional: if condition { ... } else { ... }
Comparisons: ==, !=, <, >, <=, >=. Arithmetic: +, -, *, /, %.
"""
EXAMPLE = """Example (NOT an evaluation case):
n: i64 = 5;
if n > 4 {
    print(n + 1);
} else {
    print(0);
}
The program prints 6.
"""

# Explicit public pilot items; DO NOT use these as a private holdout.
CASES = (
    ("arithmetic", "a: i64 = 7;\nb: i64 = 5;\nprint(a * 2 + b);", "19"),
    ("array_loop", """values: [i64; 4] = [5, 1, 9, 2];
mut total: i64 = 0;
for (mut i: i64 = 0; i < 4; i = i + 1) {
    if values[i] > 2 {
        total = total + values[i];
    }
}
print(total);""", "14"),
    ("while_division", """mut n: i64 = 13;
mut steps: i64 = 0;
while n > 0 {
    n = n / 2;
    steps = steps + 1;
}
print(steps);""", "4"),
)


def make_prompt(code: str, condition: str) -> str:
    if condition not in ("baseline", "spec", "examples"):
        raise ValueError(f"unknown condition: {condition}")
    context = ""
    if condition in ("spec", "examples"):
        context = f"Language reference:\n{SPEC}\n"
    if condition == "examples":
        context += f"Worked example:\n{EXAMPLE}\n"
    return (
        "You are reading a program written in Cerune, a programming language.\n"
        + context
        + "Without running code or calling tools, predict its exact printed integer.\n"
        + "Answer with the integer only, no explanation, no code fence.\n"
        + f"Program:\n```ceru\n{code}\n```"
    )


def evaluate_condition(llm, condition: str) -> float:
    correct = 0
    for index, (_case_id, code, expected) in enumerate(CASES):
        # Each prompt starts a new context: the example cannot leak to baseline.
        with kbench.chats.new(f"cerune-{condition}-{index}"):
            response = llm.prompt(make_prompt(code, condition))
        correct += str(response).strip() == expected
    return correct / len(CASES)


@kbench.task(name="cerune-output-baseline-v1")
def cerune_output_baseline(llm) -> float:
    """Predict Cerune output with no supplied language reference."""
    return evaluate_condition(llm, "baseline")


@kbench.task(name="cerune-output-spec-v1")
def cerune_output_spec(llm) -> float:
    """Predict Cerune output after reading a minimal language reference."""
    return evaluate_condition(llm, "spec")


@kbench.task(name="cerune-output-examples-v1")
def cerune_output_examples(llm) -> float:
    """Predict Cerune output with a reference and one worked example."""
    return evaluate_condition(llm, "examples")


# %%
# Build one Kaggle Task per notebook. Change the selected call and task name
# in a separate notebook to build baseline and examples independently.
# This notebook builds the specification condition.
cerune_output_spec.run(llm=kbench.llm)
