# Contributing

Thanks for your interest in improving these ADK learning notes!

## What This Repo Is

Source-traced documentation for [Google ADK (Agent Development Kit)](https://github.com/google/adk-python). Every claim is verified against the actual source code. This is NOT the official ADK documentation — see [google.github.io/adk-docs](https://google.github.io/adk-docs/) for that.

## How to Contribute

### Fixing Errors

If you find a factual error (wrong class name, wrong method signature, outdated API):

1. Verify the correct answer against the [ADK source](https://github.com/google/adk-python)
2. Open a PR with the fix
3. Include the source file and line number in your PR description

### Adding Content

New documentation should follow the template in [CLAUDE.md](CLAUDE.md#documentation-preferences):

- **At a Glance** — compact visual (5-10 lines)
- **Key API** — fields, methods, types
- **Examples** — copy-pasteable code with correct imports
- **How It Works** — detailed flows with tree-style diagrams
- **Gotchas** — traps and anti-patterns
- **Related** — cross-references to other files

### Diagram Style

Use **indented tree style** for execution flows:

```
Runner.run_async()
│
├── 1. PREPROCESS
│      build LlmRequest
│
├── 2. CALL LLM
│      model.generate_content_async()
│
└── 3. LOOP?
       function calls → repeat
       final text → exit
```

Each node on its own line. Description on the next line, indented. Blank line between siblings. See [CLAUDE.md](CLAUDE.md#diagram-quality-rules-mandatory) for the full rules.

### What NOT to Do

- Don't add runnable code or build artifacts — this is a docs-only repo
- Don't duplicate content — link to the canonical location instead
- Don't use `[ ]` checkboxes in headings
- Don't put links inside code blocks (they aren't clickable)

## File Headers

Every `adk/*.md` file should have this header format on line 3:

```text
> **Official docs:** [Topic](url) | **Source:** [`file.py`](github-url) | **Prereqs:** [Prereq Title](NN-prereq.md)
```

Note: Replace `url`, `github-url`, and `NN-prereq.md` with actual values.

## ADK Version

These notes are traced against ADK v1.27.2 ([commit `15ddf2d`](https://github.com/google/adk-python/commit/15ddf2d50d9cca31d641c1c2aa572a2415198454)). If the ADK source has changed, please update the documentation to match.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
