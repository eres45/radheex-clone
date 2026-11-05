import re

with open('static/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

games = re.findall(r"game === ['\"]([a-zA-Z0-9_-]+)['\"]", text)
print("Games supported in casinoGame:", len(games))
print(games)
