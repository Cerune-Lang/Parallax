"""Public Cerune-specific semantics v2 pilot.
Paste into a NEW cell in the current Kaggle notebook and run the cell.
The source programs are NOT executed in the notebook.
"""
import kaggle_benchmarks as kbench
kbench.config.enable_console_mode(quiet=False, color=None)

CERUNE_SEMANTIC_REFERENCE = "Cerune rules (apply these literally):\n- print(value) writes value and newline.\n- Array assignment copies values independently (not reference-sharing).\n  array_copy([10,20]) creates an independently owned dynamic [i64].\n- for (item: i64 in arr) iterates over a snapshot copied at loop entry.\n  Mutating the original arr during the loop does not change visited items.\n- byte_len(text) counts UTF-8 bytes, not Unicode characters;\n  \\u{301} inserts the U+0301 combining mark (2 UTF-8 bytes).\n- Boolean && and || are short-circuiting.\n- array_repeat::<T>(value, count) evaluates value even when count = 0.\n- Integer arithmetic is checked: overflowing i32 stops execution with\n  runtime error code integer-overflow. Earlier printed output is preserved.\n"
CERUNE_SEMANTIC_CASES = [
  {
    "id": "owned_array_copy",
    "code": "mut values: [i64] = array_copy([10, 20, 30]);\nsaved: [i64] = values;\nvalues[1] = 99;\nprint(saved[1]);\nprint(values[1]);",
    "expected": "OK:20,99"
  },
  {
    "id": "iteration_snapshot",
    "code": "mut values: [i64; 3] = [1, 2, 3];\nfor (item: i64 in values) {\n    print(item);\n    values[0] = 99;\n}\nprint(values[0]);",
    "expected": "OK:1,2,3,99"
  },
  {
    "id": "utf8_byte_len",
    "code": "print(byte_len(\"日本語\"));\nprint(byte_len(\"e\\u{301}\"));",
    "expected": "OK:9,3"
  },
  {
    "id": "short_circuit",
    "code": "print(false && 1 / 0 > 0);\nprint(true || 1 / 0 > 0);",
    "expected": "OK:false,true"
  },
  {
    "id": "zero_repeat_evaluation",
    "code": "fn source() -> i64 {\n    print(77);\n    return 9;\n}\nvalues: [i64] = array_repeat::<i64>(source(), 0);\nprint(array_len(values));",
    "expected": "OK:77,0"
  },
  {
    "id": "checked_overflow",
    "code": "print(5);\nprint(2147483647i32 + 1);",
    "expected": "ERROR:integer-overflow:5"
  }
]

def semantic_prompt(item, with_spec):
    context = ("Cerune language reference:\n" + CERUNE_SEMANTIC_REFERENCE + "\n") if with_spec else ""
    return (
        "Interpret this Cerune program without tools or code execution.\n"
        + context
        + "Return exactly OK:<comma-separated printed lines> when it succeeds.\n"
        + "Return exactly ERROR:<runtime-error-code>:<comma-separated printed lines> if it fails.\n"
        + "No spaces, no Markdown, no explanations. Booleans are lowercase.\n"
        + "Source:\n```ceru\n" + item["code"] + "\n```"
    )

# Narrow, explicit format normalization: do not change actual printed values.
CERUNE_KNOWN_ERROR_CODES = {
    "integer-overflow", "division-by-zero", "division-overflow",
    "array-index-out-of-bounds", "array-range-out-of-bounds",
    "array-length-out-of-range", "allocation-limit-exceeded",
    "allocation-size-overflow", "allocation-failed",
}

def cerune_normalize_error_code(response):
    raw = str(response).strip()
    parts = raw.split(":", 2)
    if len(parts) != 3 or parts[0] != "ERROR":
        return raw
    canonical = parts[1].lower().replace("_", "-")
    if canonical not in CERUNE_KNOWN_ERROR_CODES:
        return raw
    return "ERROR:" + canonical + ":" + parts[2]


def semantic_score(llm, with_spec):
    strict_passed = 0
    semantic_passed = 0
    for index, item in enumerate(CERUNE_SEMANTIC_CASES):
        variant = "spec" if with_spec else "baseline"
        with kbench.chats.new(f"cerune-semantics-v2-{variant}-{index}"):
            response = llm.prompt(semantic_prompt(item, with_spec))
        actual = str(response).strip()
        strict_correct = actual == item["expected"]
        semantic_correct = cerune_normalize_error_code(actual) == cerune_normalize_error_code(item["expected"])
        strict_passed += int(strict_correct)
        semantic_passed += int(semantic_correct)
        print(f"{item['id']}: {'PASS' if strict_correct else 'FAIL'}"
              f" | semantic={'PASS' if semantic_correct else 'FAIL'}"
              f" | actual={actual!r} | expected={item['expected']!r}")
    n = len(CERUNE_SEMANTIC_CASES)
    print(f"STRICT: {strict_passed}/{n} | SEMANTIC: {semantic_passed}/{n}")
    return strict_passed / n  # Kaggle RESULT remains strict for comparability.

@kbench.task(name="cerune-semantics-baseline-v2")
def cerune_semantics_baseline_v2(llm) -> float:
    return semantic_score(llm, False)

@kbench.task(name="cerune-semantics-spec-v2")
def cerune_semantics_spec_v2(llm) -> float:
    return semantic_score(llm, True)

# Run both in this notebook (6 model calls each).
cerune_semantics_baseline_v2.run(llm=kbench.llm)
cerune_semantics_spec_v2.run(llm=kbench.llm)
