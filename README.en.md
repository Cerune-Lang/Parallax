# Parallax

[日本語](README.md) | English

Parallax is the official execution-path differential testing project for [Cerune](https://github.com/Cerune-Lang/Cerune).

It compares standard output and exit status across IR (`run`), MIR (`run-mir`), and VM (`run-vm`) for the same source.

```sh
python3 scripts/differential.py --binary /path/to/cerune --cases cases
```

Each `.ceru` file has a matching `.expected` file containing the expected stdout bytes. GitHub Actions builds Cerune from source.

**The current test harness handles small success-path cases only.** Runtime-error equivalence, native codegen, and fuzzing are future work. Passing tests is not proof of safety.

For contributions and private security reports, see [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md). Reproduction-focused examples belong in [Fracta](https://github.com/Cerune-Lang/Fracta). No license has been selected yet.
