import re

with open("backend/app.py", "r", encoding="utf-8") as f:
    text = f.read()

# Force DEMO_MODE off completely
text = re.sub(r'DEMO_MODE = os.getenv\("DEMO_MODE", "false"\).lower\(\) == "true"', 'DEMO_MODE = False', text)

# Completely clear the block `if use_demo: ...` and replace with nothing
text = re.sub(r'\s*if use_demo:.*?(?=\s*if raw_packet and raw_packet.get\("valid"\):)', '\n            ', text, flags=re.DOTALL)

with open("backend/app.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Demo stripped")
