import sys, re
sys.stdout.reconfigure(encoding='utf-8')

emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\u25b6-\u25c0]')

for fname in ['templates/index.html', 'static/app.js', 'static/style.css']:
    with open(fname, 'r', encoding='utf-8') as f:
        text = f.read()
    matches = []
    for i, line in enumerate(text.splitlines()):
        found = emoji_pattern.findall(line)
        if found:
            # ignore star ★/☆ used as pin rating if acceptable, or check
            matches.append((i+1, ''.join(found), line.strip()[:80]))
    print(f'=== {fname}: {len(matches)} lines with emoji/symbols ===')
    for line_no, ems, preview in matches[:30]:
        print(f'  L{line_no}: {ems} -> {preview}')
