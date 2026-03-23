#!/usr/bin/env bash
# Pre-commit validation script — runs all checks from CLAUDE.md
# Usage: bash scripts/validate.sh
# Exit codes: 0 = pass, 1 = blocking errors found
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

errors=0
warnings=0

pass()  { printf "  \033[32m✓\033[0m %s\n" "$1"; }
fail()  { printf "  \033[31m✗\033[0m %s\n" "$1"; errors=$((errors + 1)); }
warn()  { printf "  \033[33m!\033[0m %s\n" "$1"; warnings=$((warnings + 1)); }

echo "Running validation checks..."
echo ""

# §1: Heading checkboxes
echo "§1 Heading checkboxes"
if grep -rn '^#.*\[ \]' adk/*.md python/*.md reference/*.md README.md 2>/dev/null; then
  fail "Found [ ] checkboxes in headings"
else
  pass "No heading checkboxes"
fi
echo ""

# §2: Heading spacing
echo "§2 Heading spacing"
found=false
for pattern in '^##[A-Z]' '^###[A-Z]' '^####[A-Z]'; do
  if grep -rn "$pattern" adk/*.md python/*.md reference/*.md 2>/dev/null; then
    found=true
  fi
done
if [ "$found" = true ]; then
  fail "Missing space after # in heading(s)"
else
  pass "All headings have correct spacing"
fi
echo ""

# §3: Stale b-suffix cross-references
# Canonical b-suffix files (19b-, 20b-, 22b-, 22c-) are intentional — exclude them.
# Only flag references to OLD b-suffix names that were renamed away (e.g., 07b-events.md).
echo "§3 Stale b-suffix references"
if grep -rn '[0-9]\+b-[a-z].*\.md' adk/*.md python/*.md reference/*.md 2>/dev/null \
   | grep -v '19b-security-checklist\|20b-debugging-guide\|22b-testing-context-setup\|22c-testing-examples'; then
  fail "Found stale b-suffix file references"
else
  pass "No stale b-suffix references"
fi
echo ""

# §4: Relative source paths
echo "§4 Relative source paths"
if grep -rn '\.\./adk-python/' adk/*.md python/*.md reference/*.md 2>/dev/null; then
  fail "Found ../adk-python/ relative paths — use GitHub URLs"
else
  pass "No relative source paths"
fi
echo ""

# §5: Line-3 header format
echo "§5 Header format (adk/*.md line 3)"
header_ok=true
for f in adk/*.md; do
  header=$(sed -n '3p' "$f")
  if echo "$header" | grep -q '^>' ; then
    if ! echo "$header" | grep -q 'Official docs:'; then
      echo "    $f: missing 'Official docs:' on line 3"
      header_ok=false
    fi
  fi
done
if [ "$header_ok" = true ]; then
  pass "All adk/*.md headers correct"
else
  fail "Some adk/*.md files have incorrect line-3 headers"
fi
echo ""

# §6: File length limits
echo "§6 File length limits"
length_ok=true
for f in adk/*.md; do
  lines=$(wc -l < "$f")
  if [ "$lines" -gt 600 ]; then
    warn "$f: $lines lines (limit 600)"
    length_ok=false
  fi
done
for f in python/*.md; do
  [ -f "$f" ] || continue
  lines=$(wc -l < "$f")
  if [ "$lines" -gt 1000 ]; then
    warn "$f: $lines lines (limit 1000)"
    length_ok=false
  fi
done
if [ -f "adk/00-onboarding-guide.md" ]; then
  lines=$(wc -l < "adk/00-onboarding-guide.md")
  if [ "$lines" -gt 250 ]; then
    warn "adk/00-onboarding-guide.md: $lines lines (limit 250)"
    length_ok=false
  fi
fi
if [ "$length_ok" = true ]; then
  pass "All files within length limits"
fi
echo ""

# §7: Reserved agent name "user"
echo "§7 Reserved agent name"
real_violations=0
matches=$(grep -rn 'name="user"' adk/*.md python/*.md 2>/dev/null || true)
if [ -n "$matches" ]; then
  while IFS= read -r match; do
    [ -z "$match" ] && continue
    file=$(echo "$match" | cut -d: -f1)
    lineno=$(echo "$match" | cut -d: -f2)
    context=$(sed -n "$((lineno > 5 ? lineno - 5 : 1)),${lineno}p" "$file")
    if echo "$context" | grep -qi 'anti-pattern\|wrong\|bad\|don.t\|avoid\|never\|incorrect\|reserved\|error'; then
      : # OK — in anti-pattern example
    else
      echo "    $file:$lineno — name=\"user\" is reserved"
      real_violations=$((real_violations + 1))
    fi
  done <<< "$matches"
fi
if [ "$real_violations" -gt 0 ]; then
  fail "Found $real_violations use(s) of reserved agent name 'user'"
else
  pass "No invalid uses of reserved agent name"
fi
echo ""

# §8: Links inside code blocks
echo "§8 Links inside code blocks"
url_in_code=0
for f in adk/*.md python/*.md reference/*.md; do
  [ -f "$f" ] || continue
  in_code=false
  in_mermaid=false
  lineno=0
  while IFS= read -r line; do
    lineno=$((lineno + 1))
    if echo "$line" | grep -q '^```'; then
      if [ "$in_code" = true ]; then
        in_code=false
        in_mermaid=false
      else
        in_code=true
        if echo "$line" | grep -q '^```mermaid'; then in_mermaid=true; fi
      fi
      continue
    fi
    if [ "$in_code" = true ] && [ "$in_mermaid" = false ] && echo "$line" | grep -q 'https://'; then
      if echo "$line" | grep -q '# Source:'; then continue; fi
      warn "$f:$lineno — URL inside code block not clickable"
      url_in_code=$((url_in_code + 1))
    fi
  done < "$f"
done
if [ "$url_in_code" -eq 0 ]; then
  pass "No URLs inside code blocks"
fi
echo ""

# §9: Vale prose linting
echo "§9 Prose quality (vale)"
if command -v vale &>/dev/null; then
  vale_output=$(vale --no-exit --output=line adk/ python/ reference/ 2>&1 || true)
  if [ -n "$vale_output" ]; then
    echo "$vale_output" | head -20
    vale_count=$(echo "$vale_output" | wc -l | tr -d ' ')
    warn "Vale found $vale_count issue(s)"
  else
    pass "Vale: no issues"
  fi
else
  warn "Vale not installed — skipping prose checks (brew install vale)"
fi
echo ""

# Broken relative links
echo "Broken relative links"
errfile="/tmp/ci_validate_link_errors_$$"
rm -f "$errfile"
set +o pipefail
for f in adk/*.md python/*.md reference/*.md README.md CONTRIBUTING.md; do
  [ -f "$f" ] || continue
  # Extract markdown links: ](path) — skip URLs, anchors, code blocks, and code artifacts
  # First strip fenced code blocks, then extract links
  awk '/^```/{skip=!skip; next} !skip{print}' "$f" | \
  grep -oP '\]\(\K[^)]+' 2>/dev/null | \
    grep -v '^https\?://' | \
    grep -v '^#' | \
    grep -v '\[' | \
    grep '\.md\|\.png\|\.jpg\|\.svg' | \
    sed 's/#.*//' | \
    while read -r link; do
      [ -z "$link" ] && continue
      dir=$(dirname "$f")
      target="$dir/$link"
      if [ ! -f "$target" ]; then
        echo "    $f: broken link → $link"
        echo "BROKEN" >> "$errfile"
      fi
    done
done
set -o pipefail
if [ -f "$errfile" ]; then
  count=$(wc -l < "$errfile")
  rm -f "$errfile"
  fail "Found $count broken link(s)"
else
  pass "All relative links resolve"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$errors" -gt 0 ]; then
  printf "\033[31mFAILED: %d error(s), %d warning(s)\033[0m\n" "$errors" "$warnings"
  exit 1
elif [ "$warnings" -gt 0 ]; then
  printf "\033[33mPASSED with %d warning(s)\033[0m\n" "$warnings"
  exit 0
else
  printf "\033[32mPASSED: all checks clean\033[0m\n"
  exit 0
fi
