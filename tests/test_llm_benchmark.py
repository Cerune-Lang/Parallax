"""Pure tests for the LLM benchmark; these do not invoke an LLM."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1] / "benchmarks" / "llm"
sys.path.insert(0, str(ROOT))
import codegen_eval as bench


class BenchmarkContractTests(unittest.TestCase):
    def test_all_conditions(self):
        for task in bench.CASES:
            prompts = [bench.build_prompt(task, variant)
                       for variant in ("baseline", "spec", "examples")]
            self.assertEqual(len(set(prompts)), 3)
            self.assertNotIn("Language reference:", prompts[0])
            self.assertIn("Language reference:", prompts[1])
            self.assertNotIn("Worked example:", prompts[1])
            self.assertIn("Worked example:", prompts[2])
            self.assertNotIn("9999", prompts[1])

    def test_source_normalization(self):
        source = ROOT.joinpath("fixtures", "clamp.ceru").read_text(encoding="utf-8")
        self.assertEqual(bench.extract_source(source).strip(), source.strip())
        self.assertEqual(
            bench.extract_source("```ceru\n" + source.strip() + "\n```").strip(),
            source.strip(),
        )

    def test_invalid_sources(self):
        samples = [
            "print(1);",
            'import "std:fs" as fs;\nfn solve(x: i64) -> i64 { return x; }',
            "fn solve(x: i64) -> i64 { print(x); return x; }",
            "fn solve(x: i64) -> i64 { return x; }\nfn other() -> void {}",
            "fn main() -> void {}",
            "x" * 10000,
        ]
        for sample in samples:
            with self.subTest(sample=sample[:40]), self.assertRaises(ValueError):
                bench.extract_source(sample)

    def test_reference_cases(self):
        for task, data in bench.CASES.items():
            self.assertGreaterEqual(len(data["tests"]), 5)
            inputs = [x for x, _ in data["tests"]]
            self.assertEqual(len(inputs), len(set(inputs)))
        self.assertEqual(dict(bench.CASES["sum_squares"]["tests"])[3], 14)

    def test_kaggle_module_syntax_and_contract(self):
        source = ROOT.joinpath("kaggle_task.py").read_text(encoding="utf-8")
        compile(source, str(ROOT / "kaggle_task.py"), "exec")
        self.assertEqual(source.count("@kbench.task("), 3)
        self.assertIn("kbench.chats.new(", source)


if __name__ == "__main__":
    unittest.main()
