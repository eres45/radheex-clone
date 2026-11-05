import re

files = ['tests/test_admin.py', 'tests/test_audit_regressions.py', 'tests/test_live_feed.py', 'tests/test_opt_pass.py']
for f in files:
    content = open(f, encoding='utf-8').read()
    print(f"=== {f} ===")
    funcs = re.findall(r'def (test_[a-zA-Z0-9_]+)\(', content)
    for fn in funcs:
        body_match = re.search(r'def ' + fn + r'\(.*?\n(?=(?:def |\Z))', content, re.DOTALL)
        if body_match and 'load_sample' in body_match.group(0):
            print("  -", fn)
