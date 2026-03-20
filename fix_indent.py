#!/usr/bin/env python3
"""Fix Python code block indentation in Markdown files.

All ```python blocks have been collapsed to 1-space indentation.
This script reconstructs proper indentation using Python syntax analysis.
"""

import re
import sys
from pathlib import Path

INDENT = 2  # spaces per level


def count_net_parens(line: str) -> int:
    """Count net open parens, ignoring those inside strings."""
    depth = 0
    in_str = None
    i = 0
    while i < len(line):
        ch = line[i]
        if in_str:
            if ch == '\\':
                i += 2
                continue
            if ch == in_str:
                # Check for triple quote
                if line[i:i+3] in ('"""', "'''"):
                    in_str = None
                    i += 3
                    continue
                in_str = None
        else:
            if line[i:i+3] in ('"""', "'''"):
                in_str = ch
                i += 3
                continue
            if ch in ('"', "'"):
                in_str = ch
            elif ch in '([{':
                depth += 1
            elif ch in ')]}':
                depth -= 1
            elif ch == '#':
                break  # rest is comment
        i += 1
    return depth


def ends_with_colon(line: str) -> bool:
    """Check if line ends with : (block opener), ignoring comments and strings."""
    stripped = line.strip()
    if stripped.startswith('#'):
        return False
    # Remove trailing comment
    result = ''
    in_str = None
    i = 0
    while i < len(stripped):
        ch = stripped[i]
        if in_str:
            if ch == '\\':
                result += ch + (stripped[i+1] if i+1 < len(stripped) else '')
                i += 2
                continue
            result += ch
            if ch == in_str:
                in_str = None
        else:
            if ch in ('"', "'"):
                in_str = ch
                result += ch
            elif ch == '#':
                break
            else:
                result += ch
        i += 1
    return result.rstrip().endswith(':')


def is_decorator(line: str) -> bool:
    return line.strip().startswith('@')


def is_class_def(line: str) -> bool:
    return bool(re.match(r'^class\s+', line.strip()))


def is_func_def(line: str) -> bool:
    return bool(re.match(r'^(async\s+)?def\s+', line.strip()))


def is_method(line: str) -> bool:
    """Check if a def has self/cls as first parameter."""
    s = line.strip()
    # Match def name(self or def name(cls
    return bool(re.search(r'def\s+\w+\s*\(\s*(self|cls)\b', s))


def has_self_or_cls_continuation(lines: list, start_idx: int) -> bool:
    """For multi-line signatures, check if self/cls appears in continuation."""
    for i in range(start_idx + 1, min(start_idx + 5, len(lines))):
        s = lines[i].strip()
        if re.match(r'^(self|cls)\s*[,:]', s) or s in ('self,', 'cls,', 'self', 'cls'):
            return True
        if s.startswith(')'):
            break
    return False


def fix_python_block(lines: list) -> list:
    """Reconstruct proper indentation for a Python code block."""
    result = []
    indent_stack = [0]  # Stack of indent levels for blocks
    paren_depth = 0
    paren_base_indent = 0
    in_multiline_string = False
    ml_string_indent = 0

    # Pre-scan: find class definitions to know about class scope
    class_line_indices = set()
    for i, line in enumerate(lines):
        if is_class_def(line):
            class_line_indices.add(i)

    # Track if we're "inside" a class body
    class_body_indent = -1  # -1 means not in a class

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Empty line
        if not stripped:
            result.append('')
            i += 1
            continue

        # Handle multi-line strings (docstrings)
        if in_multiline_string:
            result.append(' ' * ml_string_indent + stripped)
            if '"""' in stripped or "'''" in stripped:
                # Count quotes to see if this closes
                count = stripped.count('"""') + stripped.count("'''")
                if count >= 1:
                    in_multiline_string = False
            i += 1
            continue

        # Determine this line's indent
        current_indent = indent_stack[-1]

        # --- LEADING CLOSE PARENS ---
        if stripped[0] in ')]}':
            if paren_depth > 0:
                # Close paren goes at the level of the opening line
                current_indent = paren_base_indent
                paren_depth += count_net_parens(stripped)
                paren_depth = max(0, paren_depth)
                if paren_depth == 0:
                    # Check if this line also ends with : (like `) -> ReturnType:`)
                    if ends_with_colon(stripped):
                        result.append(' ' * current_indent + stripped)
                        indent_stack.append(current_indent + INDENT)
                        i += 1
                        continue
                result.append(' ' * current_indent + stripped)
                i += 1
                continue

        # --- CONTINUATION INSIDE PARENS ---
        if paren_depth > 0:
            current_indent = paren_base_indent + INDENT
            result.append(' ' * current_indent + stripped)
            paren_depth += count_net_parens(stripped)
            paren_depth = max(0, paren_depth)
            if paren_depth == 0 and ends_with_colon(stripped):
                indent_stack.append(current_indent + INDENT)
            i += 1
            # Check for docstring start
            if '"""' in stripped or "'''" in stripped:
                q = '"""' if '"""' in stripped else "'''"
                cnt = stripped.count(q)
                if cnt == 1:
                    in_multiline_string = True
                    ml_string_indent = current_indent
            continue

        # --- DECORATOR ---
        if is_decorator(stripped):
            # Decorator at same level as the def/class it decorates
            # Peek ahead to see what it decorates
            if class_body_indent >= 0:
                current_indent = class_body_indent
            else:
                current_indent = indent_stack[-1]
                # Check if this follows a return/yield/pass which would mean we're back up
                # Keep at current indent level
            result.append(' ' * current_indent + stripped)
            i += 1
            continue

        # --- CLASS DEF ---
        if is_class_def(stripped):
            # Classes in doc examples are usually top-level
            current_indent = 0
            class_body_indent = INDENT
            # Reset indent stack
            indent_stack = [0]
            result.append(' ' * current_indent + stripped)

            paren_depth += count_net_parens(stripped)
            if paren_depth > 0:
                paren_base_indent = current_indent

            if ends_with_colon(stripped) and paren_depth == 0:
                indent_stack.append(INDENT)

            i += 1
            continue

        # --- FUNCTION/METHOD DEF ---
        if is_func_def(stripped):
            if is_method(stripped) or (class_body_indent >= 0 and has_self_or_cls_continuation(lines, i)):
                # It's a method inside a class
                current_indent = class_body_indent
            elif class_body_indent >= 0:
                # A function inside a class without self — could be static or nested
                # Check if there's a @staticmethod or @classmethod above
                prev_stripped = ''
                for j in range(i-1, max(i-3, -1), -1):
                    ps = lines[j].strip()
                    if ps:
                        prev_stripped = ps
                        break
                if prev_stripped.startswith('@'):
                    current_indent = class_body_indent
                else:
                    # Standalone function after class code
                    current_indent = 0
                    class_body_indent = -1
                    indent_stack = [0]
            else:
                # Top-level function
                current_indent = 0
                indent_stack = [0]

            result.append(' ' * current_indent + stripped)

            paren_depth += count_net_parens(stripped)
            if paren_depth > 0:
                paren_base_indent = current_indent

            if ends_with_colon(stripped) and paren_depth == 0:
                indent_stack = [lvl for lvl in indent_stack if lvl <= current_indent]
                if not indent_stack:
                    indent_stack = [0]
                indent_stack.append(current_indent + INDENT)

            i += 1
            continue

        # --- DEDENT KEYWORDS ---
        if re.match(r'^(else\s*:|elif\s|except\s|except:|finally:)', stripped):
            # Go back one indent level from current
            if len(indent_stack) > 1:
                indent_stack.pop()
            current_indent = indent_stack[-1]
            result.append(' ' * current_indent + stripped)
            if ends_with_colon(stripped):
                indent_stack.append(current_indent + INDENT)
            i += 1
            continue

        # --- REGULAR LINE ---
        current_indent = indent_stack[-1]
        result.append(' ' * current_indent + stripped)

        # Track paren depth
        net = count_net_parens(stripped)
        if net > 0:
            paren_base_indent = current_indent
            paren_depth = net

        # Block opener
        if ends_with_colon(stripped) and paren_depth == 0:
            indent_stack.append(current_indent + INDENT)

        # Check for docstring start
        for q in ('"""', "'''"):
            if q in stripped:
                cnt = stripped.count(q)
                if cnt == 1:  # Opening docstring not closed on same line
                    in_multiline_string = True
                    ml_string_indent = current_indent
                    # But if it's the start of a docstring at class/method level
                    if indent_stack[-1] > current_indent:
                        ml_string_indent = indent_stack[-1]
                    break

        i += 1

    return result


def process_markdown_file(filepath: Path) -> bool:
    """Process a single markdown file. Returns True if changes were made."""
    content = filepath.read_text()
    lines = content.split('\n')
    result = []
    i = 0
    changed = False

    while i < len(lines):
        line = lines[i]

        # Check for ```python block start
        if line.strip() == '```python':
            result.append(line)
            i += 1

            # Collect the block
            block_lines = []
            while i < len(lines) and lines[i].strip() != '```':
                block_lines.append(lines[i])
                i += 1

            # Check if block has 1-space indentation issues
            has_1space = any(
                l.startswith(' ') and not l.startswith('  ') and l.strip()
                for l in block_lines
            )

            if has_1space:
                fixed = fix_python_block(block_lines)
                if fixed != block_lines:
                    changed = True
                result.extend(fixed)
            else:
                result.extend(block_lines)

            # Add closing ```
            if i < len(lines):
                result.append(lines[i])
                i += 1
        else:
            result.append(line)
            i += 1

    if changed:
        filepath.write_text('\n'.join(result))

    return changed


def main():
    adk_dir = Path('/Users/weizheng/Documents/learning/learning-adk/adk')
    files = sorted(adk_dir.glob('*.md'))

    for f in files:
        changed = process_markdown_file(f)
        status = 'FIXED' if changed else 'no change'
        print(f'{f.name}: {status}')


if __name__ == '__main__':
    main()
