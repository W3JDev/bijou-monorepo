"""Check for missing i18n keys referenced in components."""
import re
from pathlib import Path

i18n_text = Path('i18n.ts').read_text(encoding='utf-8')
i18n_keys = set(re.findall(r'^\s{6}"([\w.\-]+)"\s*:', i18n_text, re.MULTILINE))

# Find all t("...") calls in components
components = list(Path('components').glob('*.tsx')) + [Path('App.tsx')]
referenced = set()
for f in components:
    if not f.exists():
        continue
    text = f.read_text(encoding='utf-8', errors='ignore')
    for m in re.finditer(r'\bt\(\s*["\']([\w.\-]+)["\']', text):
        referenced.add(m.group(1))
    for m in re.finditer(r't\(\s*["\']([\w.\-]+)["\']\s*,\s*\{', text):
        referenced.add(m.group(1))

missing = referenced - i18n_keys
extra_in_code = sorted(referenced)
print(f'i18n.ts has {len(i18n_keys)} keys')
print(f'Components reference {len(referenced)} unique keys')
print(f'MISSING in i18n.ts (referenced but not defined): {len(missing)}')
for k in sorted(missing):
    print(f'  - {k}')

# Check keys defined but not referenced
unused = i18n_keys - referenced
print(f'\nUNUSED keys (defined in i18n.ts but no component references them): {len(unused)}')
for k in sorted(unused)[:30]:
    print(f'  - {k}')
if len(unused) > 30:
    print(f'  ... and {len(unused) - 30} more')
