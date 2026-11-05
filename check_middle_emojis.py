import sys, re
sys.stdout.reconfigure(encoding='utf-8')

emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\u25b6-\u25c0]')

with open('static/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

idx_home = text.find('async function homeView()')
idx_casino = text.find('function casinoLobby(')

block = text[idx_home:idx_casino]
matches = emoji_pattern.findall(block)
print(f'Emojis between homeView and casinoLobby: {len(matches)}')
for line in block.splitlines():
    found = emoji_pattern.findall(line)
    if found:
        print(f'{found} -> {line.strip()[:80]}')
