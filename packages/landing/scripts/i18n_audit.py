"""One-shot i18n audit: per-language key counts, dupes, missing keys vs EN."""
import re
from pathlib import Path
from collections import Counter

src = Path(r"C:\Users\W3jde\local-projects\Bijou-AI---Digital-Employee-main\Bijou-AI---Digital-Employee-main\i18n.ts").read_text(encoding="utf-8")

# Split on top-level "  xx: {" blocks. Each starts with 2-space indent and ends before next 2-space-indented key.
def extract_blocks(text):
    blocks = {}
    pattern = re.compile(r'^  ([a-z]{2,3}): \{\s*$', re.MULTILINE)
    matches = list(pattern.finditer(text))
    for i, m in enumerate(matches):
        lang = m.group(1)
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        blocks[lang] = text[start:end]
    return blocks

def extract_keys(block):
    # Match keys at 6-space indent like:      "foo.bar": "value"
    return re.findall(r'^\s{6}"([\w.\-]+)"\s*:', block, re.MULTILINE)

blocks = extract_blocks(src)
print("Languages found:", list(blocks.keys()))
print()

# Duplicate-key detection per language
for lang, block in blocks.items():
    keys = extract_keys(block)
    counts = Counter(keys)
    dupes = {k: v for k, v in counts.items() if v > 1}
    print(f"  {lang}: {len(keys)} key entries, {len(set(keys))} unique, {len(dupes)} duplicate keys")
    if dupes:
        for k, v in sorted(dupes.items())[:10]:
            print(f"      DUPE: {k!r} appears {v}x")

# Missing keys: which keys exist in en but not in others?
en_keys = set(extract_keys(blocks['en']))
print()
print("=== Missing-key report (vs EN) ===")
for lang in ['ms', 'zh', 'ta']:
    if lang not in blocks:
        print(f"  {lang}: NO BLOCK")
        continue
    other = set(extract_keys(blocks[lang]))
    missing = en_keys - other
    extra = other - en_keys
    print(f"  {lang}: missing {len(missing)} EN keys, {len(extra)} extra keys not in EN")
    if missing:
        for k in sorted(missing)[:8]:
            print(f"      MISSING: {k}")
        if len(missing) > 8:
            print(f"      ... and {len(missing) - 8} more")
