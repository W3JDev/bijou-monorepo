"""Check declared vs locked dep versions."""
import re
import json

text = open('package.json', encoding='utf-8').read()
lock = json.load(open('package-lock.json', encoding='utf-8'))
pkgs = lock.get('packages', {})

# Parse declared deps
declared = {}
pj = json.loads(text)
declared.update(pj.get('dependencies', {}))
declared.update(pj.get('devDependencies', {}))

for name in sorted(declared):
    declared_ver = declared[name]
    locked = pkgs.get(f'node_modules/{name}', {}).get('version', '?')
    sigil = declared_ver[:1]
    print(f'  {name:40s} declared: {sigil}{declared_ver[1:]:8s} locked: {locked}')

# Also count total locked packages
print(f'\nTotal locked packages: {len(pkgs)}')
