import json
import os

OUTPUT_DIR = r"g:\project\radhesite\network-reverse"

profile = {
    "username": "mataji060",
    "name": "Demo",
    "role": "Client",
    "level": 6,
    "parentId": "10bhavesh",
    "parents": ["10bhavesh", "jaguar24", "jaguarwbx", "1xb", "operator"],
    "creditRef": 100,
    "balance": 100,
    "availableBalance": 100,
    "exposure": 0,
    "pnl": 0,
    "sharingDetail": {
        "sports": 90,
        "others": 90,
        "casino": 90
    },
    "currency": "INR",
    "operatorId": "RDE"
}

hierarchy = {
    "Level 1": "operator (Master / Root Exchange)",
    "Level 2": "1xb (Super Master)",
    "Level 3": "jaguarwbx (Master)",
    "Level 4": "jaguar24 (Super Agent)",
    "Level 5": "10bhavesh (Agent / Sub-Admin)",
    "Level 6": "mataji060 (End Client / Player Account)"
}

auth_flow = {
    "login_endpoint": "POST https://api.radheex.com/sso/auth",
    "headers": {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "x-op-key": "RDE"
    },
    "payload_format": "username={username}&password={password}&requestId={uuid}&captchaAnswer={solution}",
    "captcha_endpoint": "GET https://api.radheex.com/sso/auth/requestcaptcha",
    "response_token_type": "Bearer JWT",
    "token_claims": {
        "sub": "mataji060",
        "role": "Client",
        "iss": "RDE",
        "exp": 1793765701293,
        "pwdch": False,
        "ip": "client_ip"
    }
}

with open(os.path.join(OUTPUT_DIR, "real_account_profile.json"), "w", encoding="utf-8") as f:
    json.dump(profile, f, indent=2)

with open(os.path.join(OUTPUT_DIR, "real_account_hierarchy.json"), "w", encoding="utf-8") as f:
    json.dump(hierarchy, f, indent=2)

with open(os.path.join(OUTPUT_DIR, "auth_flow_spec.json"), "w", encoding="utf-8") as f:
    json.dump(auth_flow, f, indent=2)

print("Saved real account reverse specs!")
