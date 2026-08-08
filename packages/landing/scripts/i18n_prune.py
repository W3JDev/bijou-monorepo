"""One-shot i18n dead-key pruner (v3 — multi-language aware).

Iterates over each language block (en, ms, zh, ta) and prunes the same set
of dead keys in all four. Preserves the en-defined key set as the source
of truth (after the first pass en is the smallest and others are aligned).
"""
import re
from pathlib import Path

I18N = Path('i18n.ts')
SRC_GLOB = ['components/*.tsx', 'App.tsx', 'index.tsx']

# 1. Collect all t("key") references in the codebase.
referenced = set()
for pattern in SRC_GLOB:
    for f in Path('.').glob(pattern):
        if not f.exists():
            continue
        text = f.read_text(encoding='utf-8', errors='ignore')
        for m in re.finditer(r"\bt\(\s*['\"]([\w.\-]+)['\"]", text):
            referenced.add(m.group(1))
        for m in re.finditer(r"\bt\(\s*['\"]([\w.\-]+)['\"]\s*,", text):
            referenced.add(m.group(1))

# 2. Find every key in i18n.ts.
i18n_text = I18N.read_text(encoding='utf-8')

# 3. Identify language blocks and process each one independently.
#    A block starts with `  <lang>: {` at 2-space indent and ends before
#    the next 2-space-indented `  <lang>: {` or EOF.
block_pattern = re.compile(r'^  ([a-z]{2,3}): \{\s*$', re.MULTILINE)
matches = list(block_pattern.finditer(i18n_text))

# Compute the dead set: keys defined in any block but not referenced.
defined_everywhere = set()
for m in matches:
    lang = m.group(1)
    start = m.end()
    end = matches[matches.index(m) + 1].start() if matches.index(m) + 1 < len(matches) else len(i18n_text)
    block = i18n_text[start:end]
    defined_everywhere.update(re.findall(r'^\s{6}"([\w.\-]+)"\s*:', block, re.MULTILINE))

dead = defined_everywhere - referenced
print(f'Defined: {len(defined_everywhere)}, Referenced: {len(referenced)}, Dead: {len(dead)}')

# 4. Remove dead keys from each block, one block at a time.
#    Strategy: for each dead key, find every occurrence of the key line and
#    remove the full multi-line value. Do this by re-reading the file and
#    rebuilding it block-by-block.
new_text = i18n_text
for round_count in range(2):  # run twice in case order matters
    matches = list(block_pattern.finditer(new_text))
    for m in matches:
        lang = m.group(1)
        start = m.end()
        end = matches[matches.index(m) + 1].start() if matches.index(m) + 1 < len(matches) else len(new_text)
        block = new_text[start:end]

        for key in sorted(dead, key=len, reverse=True):
            ek = re.escape(key)
            # Try single-line value first: `      "key": "value",`
            block, n1 = re.subn(
                r'^\s{6}"' + ek + r'"\s*:\s*"[^"\\]*(?:\\.[^"\\]*)*"\s*,?\s*\n',
                '',
                block,
                flags=re.MULTILINE,
            )
            if n1:
                continue
            # Try multi-line: opening line + content lines + closing line.
            # The value starts after `:` and can span lines that start with 6-space indent.
            # We'll find the opening line and then walk forward.
            lines = block.split('\n')
            out_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                m_open = re.match(r'^(\s{6})"' + ek + r'"\s*:\s*(.*)$', line)
                if m_open and (m_open.group(2).strip() == '' or m_open.group(2).lstrip().startswith('"')):
                    rest = m_open.group(2)
                    # Determine if the value is fully on this line
                    # by checking if it ends with an unescaped closing quote
                    if rest.rstrip().endswith(','):
                        # Could be a multi-line template literal or a string with
                        # a comma but no value (rare). Skip cautiously.
                        # Look ahead: if next line is purely whitespace or starts
                        # with closing-backtick/comma, treat as single-line.
                        nxt = lines[i + 1] if i + 1 < len(lines) else ''
                        if nxt.strip() in ('', '`', '`),') or nxt.startswith(('  ', '    ')) and not nxt.startswith('      "'):
                            i += 1
                            continue
                    if rest.strip() == '':
                        # Template literal starts on next line(s)
                        i += 1
                        # Eat lines until we find a backtick at the right indent
                        while i < len(lines) and not re.match(r'^\s{6}`\s*,?\s*$', lines[i]):
                            i += 1
                        if i < len(lines):
                            i += 1  # eat the closing backtick line
                        continue
                    # If rest ends with `",` or `"` at the end, single-line string
                    if re.search(r'"\s*,?\s*$', rest):
                        i += 1
                        continue
                    # Otherwise multi-line string. Walk forward.
                    i += 1
                    while i < len(lines):
                        cont = lines[i]
                        if re.match(r'^\s{6}"[^"\\]*(?:\\.[^"\\]*)*"\s*,?\s*$', cont):
                            i += 1
                            break
                        i += 1
                    continue
                out_lines.append(line)
                i += 1
            block = '\n'.join(out_lines)

        # Replace this block in new_text.
        new_text = new_text[:start] + block + new_text[end:]

# 5. Also clean up empty language-block sub-sections like a trailing
#    `// LEGACY KEYS` comment with no keys underneath.
# (Skip — keep comments for history.)

if new_text != i18n_text:
    I18N.write_text(new_text, encoding='utf-8')
    print('Wrote i18n.ts.')
else:
    print('No changes.')

# 6. Re-audit.
print('\n=== Post-prune audit ===')
