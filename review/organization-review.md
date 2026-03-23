# ADK Documentation Organization Review — Remaining Items

> Generated 2026-03-23. Completed items removed.

---

## 1. File Grouping — Add Subdirectories

- [ ] Group flat `adk/` into subdirectories (`getting-started/`, `core/`, `services/`, `operations/`, `advanced/`, `faq/`, `preview/`)
- Trade-off: breaks all cross-references. Only worth it if docs keep growing.

## 3. Merge Overlapping Content

| # | Problem | Files | Recommendation |
|---|---------|-------|----------------|
| 3b | State prefix scoping explained 3x | `08`, `19`, `24-faq Q5` | Keep in `08`. `19` keeps security angle only. Q5 becomes cross-ref |
| 3c | Latency/model selection in 2 files | `18b`, `20b` | Merge `20b` latency section into `18b`. `20b` keeps debugging only |
| 3d | Session backend selection in 3 files | `18`, `20`, `20b` | Keep table in `20` only. Others cross-ref |
| 3e | Testing pyramid in 3 files | `22`, `22c`, `24-faq Q2` | Keep in `22`. Q2 becomes 2-line answer + cross-ref |
| 3g | AgentTool vs sub_agents in 2 files | `23b`, `24c` | Keep in `24c`. `23b` cross-refs |
| 3h | Flow selection logic duplicated | `04`, `05` | Keep in `04`. `05` cross-refs |
| 3i | Migration notes duplicated | `25`, `25b` | Keep full table in `25b`. `25` cross-refs |

## 4. File Ordering Adjustments

| # | Current | Issue | Proposed |
|---|---------|-------|----------|
| 4a | `15-evaluation.md` between planners and errors | Eval is about testing, not a core service | Move after testing: `22d-evaluation.md` |
| 4c | `18b` second half is general perf | Strategies 6-10 aren't session-specific | Rename broader or move strategies 6-10 into `20b` |

## 6. Split Candidates

| # | File | Lines | What to split |
|---|------|-------|---------------|
| 6a | `22c-testing-examples.md` | 628 | Move "Best Practices" + "Quick Reference" to `22-testing.md` |
| 6b | `04-agents.md` | 536 | Move "How Agent Transfer Works" to `04b-agent-transfer.md` |
| 6c | `09-tools.md` | 439 | Move MCP + tool confirmation to `09b-mcp-and-confirmation.md` |
| 6d | `13-auth.md` | 457 | Move code examples to `13b-auth-examples.md` |
