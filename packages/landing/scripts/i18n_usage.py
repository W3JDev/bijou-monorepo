"""Survey translation usage across the codebase."""
import re
from pathlib import Path

files = sorted(list(Path('components').glob('*.tsx'))) + [Path('App.tsx')]
print('=== Translation usage per file ===')
print(f'{"file":35s} {"useT":>5s}  {"t(...)":>6s}')
for f in files:
    if not f.exists():
        continue
    text = f.read_text(encoding='utf-8', errors='ignore')
    n_useT = len(re.findall(r'useTranslation', text))
    n_t = len(re.findall(r'\bt\(\s*["\']', text))
    print(f'  {f.name:33s} {n_useT:5d}  {n_t:6d}')
