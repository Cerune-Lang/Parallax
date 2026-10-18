import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from seeded import Case, generate, minimize, size, MIN_I32, MAX_I32, load_seeds

class SeededTests(unittest.TestCase):
    def test_determinism(self):
        self.assertEqual(list(generate(1337, 30)), list(generate(1337, 30)))
        self.assertNotEqual(list(generate(1, 30)), list(generate(2, 30)))

    def test_oracle(self):
        self.assertEqual(Case(3, '+', -5).oracle(), {'kind': 'success', 'stdout': '-2\n'})
        self.assertEqual(Case(MAX_I32, '+', 1).oracle()['code'], 'integer-overflow')
        self.assertEqual(Case(MIN_I32, '-', 1).oracle()['code'], 'integer-overflow')
        self.assertEqual(Case(MIN_I32, '/', -1).oracle()['code'], 'division-overflow')
        self.assertEqual(Case(5, '/', 0).oracle()['code'], 'division-by-zero')
        self.assertEqual(Case(-7, '/', 3).oracle()['stdout'], '-2\n')

    def test_reduction(self):
        original = Case(159, '*', 92)
        def probe(case):
            return (('run-vm', 'oracle-mismatch'),) if case.left > 0 and case.right > 0 else ()
        minimized, attempts = minimize(original, probe(original), probe, 60)
        self.assertLess(size(minimized), size(original))
        self.assertEqual(probe(minimized), probe(original))
        self.assertLessEqual(attempts, 60)

    def test_corpus(self):
        corpus = Path(__file__).resolve().parents[1] / 'corpus/seeds.json'
        self.assertEqual(len(load_seeds(corpus)), 3)

if __name__ == '__main__': unittest.main()
