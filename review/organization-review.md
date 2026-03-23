# ADK Documentation Organization Review

> Generated 2026-03-23 from full audit of all 35 ADK files.

---

## 1. File Grouping — Add Subdirectories

- [ ] Group flat `adk/` into `getting-started/`, `core/`, `services/`, `operations/`, `advanced/`, `faq/`, `preview/`
- Trade-off: breaks all cross-references. Only worth it if docs keep growing. If 35 files is the ceiling, flat + nav grouping is enough.

## 2. Rename `23b-plugins-and-a2a.md`

- [x] ~~Rename to `23b-custom-tools-and-toolsets.md` — file contains zero A2A content~~ **DONE**

## 3. Merge Overlapping Content

| # | Problem | Files | Recommendation | Status |
|---|---------|-------|----------------|--------|
| 3a | DB locking explained 3x identically | `17`, `18`, `19b` | Keep in `17`. Replace in `18`/`19b` with cross-ref | **DONE** |
| 3b | State prefix scoping explained 3x | `08`, `19`, `24-faq Q5` | Keep in `08`. `19` keeps security angle only. Q5 becomes cross-ref | |
| 3c | Latency/model selection in 2 files | `18b`, `20b` | Merge `20b` latency section into `18b`. `20b` keeps debugging only | |
| 3d | Session backend selection in 3 files | `18`, `20`, `20b` | Keep table in `20` only. Others cross-ref | |
| 3e | Testing pyramid in 3 files | `22`, `22c`, `24-faq Q2` | Keep in `22`. Q2 becomes 2-line answer + cross-ref | |
| 3f | Preprocessing patterns near-duplicated | `24-faq Q3`, `24b` | Add explicit link from Q3 to `24b`. Q3 keeps summary only | **DONE** |
| 3g | AgentTool vs sub_agents in 2 files | `23b`, `24c-message-passing` | Keep in `24c`. `23b` cross-refs | |
| 3h | Flow selection logic duplicated | `04`, `05` | Keep in `04`. `05` cross-refs | |
| 3i | Migration notes duplicated | `25`, `25b` | Keep full table in `25b`. `25` cross-refs | |

## 4. File Ordering Adjustments

| # | Current | Issue | Proposed | Status |
|---|---------|-------|----------|--------|
| 4a | `15-evaluation.md` between planners and errors | Eval is about testing, not a core service | Move after testing: `22d-evaluation.md` | |
| 4b | `message-passing-patterns.md` has no number | Invisible in reading order | Renumber to `24c-message-passing-patterns.md` | **DONE** |
| 4c | `18b` second half is general perf | Strategies 6-10 aren't session-specific | Rename broader or move strategies 6-10 into `20b` | |

## 5. Standardize H2 Headings

Convention: `At a Glance → Class Hierarchy → Key API → How It Works → Examples → Gotchas → Related`

| # | File | Issue | Status |
|---|------|-------|--------|
| 5a | `11-memory.md` | "What It Is" → "At a Glance" | **DONE** |
| 5b | `12-artifacts.md` | Non-standard heading names | **DONE** |
| 5c | `13-auth.md` | "What It Is" → "At a Glance", "Auth Model Overview" → "How It Works" | **DONE** |
| 5d | `16-error-reference.md` | Already standard | OK |
| 5e | `18-session-lifecycle.md` | Already has At a Glance + How It Works | OK |
| 5f | `18b`, `19b`, `20b` | Companion files — standard not enforced | Skipped |

## 6. Split Candidates

| # | File | Lines | What to split |
|---|------|-------|---------------|
| 6a | `22c-testing-examples.md` | 628 | Move "Best Practices" + "Quick Reference" to `22-testing.md` |
| 6b | `04-agents.md` | 536 | Move "How Agent Transfer Works" to `04b-agent-transfer.md` |
| 6c | `09-tools.md` | 439 | Move MCP + tool confirmation to `09b-mcp-and-confirmation.md` |
| 6d | `13-auth.md` | 457 | Move code examples to `13b-auth-examples.md` |

## 7. Nav Grouping in `mkdocs.yml`

- [x] ~~Add section headers + missing pages (18b, 24b, 24c)~~ **DONE**

---

## Priority Order

1. ~~Rename `23b`~~ **DONE**
2. ~~Number `message-passing-patterns.md` → `24c-`~~ **DONE**
3. ~~Deduplicate DB locking (3 files → 1 + cross-refs)~~ **DONE**
4. Deduplicate latency content (`18b` vs `20b`)
5. ~~Add nav grouping in `mkdocs.yml`~~ **DONE**
6. ~~Standardize H2 headings~~ **DONE**
7. ~~Add Q3→24b link in FAQ~~ **DONE**
8. Subdirectories only if docs keep growing
