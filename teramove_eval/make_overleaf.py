"""Build overleaf/main.tex from paper.tex: inline number macros and Table II, fix image paths."""
import re, sys
root = sys.argv[1]
t = open(f'{root}/paper.tex').read()
macros = dict(re.findall(r'\\newcommand\{\\(\w+)\}\{([^}]*)\}', open(f'{root}/numbers.tex').read()))
t = t.replace('\\input{numbers.tex}\n', '')
t = t.replace('\\input{tables/tiers.tex}', open(f'{root}/tables/tiers.tex').read().rstrip('\n'))
def sub(m):
    name = m.group(1)
    return macros[name] if name in macros else m.group(0)
t = re.sub(r'\\([A-Z]\w*)(?:\{\})?', sub, t)
t = t.replace('{figures/', '{APSO_Results_ICC/')
left = [n for n in macros if '\\' + n in t]
assert not left, left
bad = [l for l in t.splitlines() if any(ord(c) > 127 for c in l)]
assert not bad, bad[:3]
open(f'{root}/overleaf/main.tex', 'w').write(t)
print('ok')
