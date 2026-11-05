import urllib.request

req = urllib.request.Request(
    'https://oddsdata.org/score/a9a34ab526857ed732b4cc0aa5802be39fca6e47/35248',
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        content = resp.read().decode('utf-8')
    print("oddsdata.org response length:", len(content))
    print("Content preview:")
    print(content[:600])
except Exception as e:
    print("Error:", e)
