import sys
sys.stdout.reconfigure(encoding='utf-8')

# 1. Update templates/index.html to use menu.svg
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

html = html.replace('<button class="menu-btn" id="menuBtn" aria-label="Menu">☰</button>',
                    '<button class="menu-btn" id="menuBtn" aria-label="Menu"><img src="/static/images/menu.svg" width="18" height="18" alt="Menu" style="filter: brightness(0) invert(1);"></button>')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Updated templates/index.html")
