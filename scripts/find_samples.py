import os
import re

files = ['tests/test_admin.py', 'tests/test_audit_regressions.py', 'tests/test_live_feed.py', 'tests/test_opt_pass.py']
samples = set()
for f in files:
    content = open(f, 'r', encoding='utf-8').read()
    found = re.findall(r'load_sample\(["\']([^"\']+)["\']\)', content)
    samples.update(found)

print("Sample files needed by tests:")
for s in sorted(samples):
    print(" -", s)
