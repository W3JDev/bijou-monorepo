"""Clean up orphan i18n value lines left over by the bulk pruner.

If a removed key had a multi-line value, the pruner may have left the value
content behind (because it only matched exact key patterns). This script
finds any line at 6-space indent that is not the start of a key (no leading
quote immediately) and removes it along with the next continuation lines.
"""
import re
from pathlib import Path

I18N = Path('i18n.ts')
text = I18N.read_text(encoding='utf-8')
lines = text.split('\n')
out = []
i = 0
removed = 0
while i < len(lines):
    line = lines[i]
    # A key-value line: 6 spaces, then "key":
    if re.match(r'^\s{6}"[\w.\-]+"\s*:', line):
        out.append(line)
        i += 1
        continue
    # A comment line: keep
    if line.strip().startswith('//') or line.strip() == '':
        out.append(line)
        i += 1
        continue
    # A closing brace or section header: keep
    if line.strip() in ('', '}', '),'):
        out.append(line)
        i += 1
        continue
    # If we get here, the line is suspicious. Look ahead to see if the next
    # few lines form a value block (orphan continuation) — if so, drop them.
    if re.match(r'^\s{6}', line) and not line.lstrip().startswith('"'):
        # This is an orphan. Eat it and any continuation lines.
        i += 1
        while i < len(lines):
            cont = lines[i]
            if re.match(r'^\s{6}"[\w.\-]+"\s*:', cont):
                break  # next key starts — done
            if cont.strip() == '' or cont.strip().startswith('//') or cont.strip() in ('}', '),'):
                break  # section ends
            if re.match(r'^\s{6}\S', cont):
                # Another orphan content line
                i += 1
                continue
            # Anything else: keep, but stop orphan-eating
            break
        removed += 1
        continue
    out.append(line)
    i += 1

new_text = '\n'.join(out)
# Collapse multiple blank lines
new_text = re.sub(r'\n{3,}', '\n\n', new_text)

if new_text != text:
    I18N.write_text(new_text, encoding='utf-8')
    print(f'Removed {removed} orphan-line blocks.')
else:
    print('No orphans found.')
