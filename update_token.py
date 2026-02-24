import os
from pathlib import Path

env_file = Path(".env")
new_token = str(os.getenv("TELEGRAM_BOT_TOKEN", "")).strip()

if not new_token:
    print("✗ TELEGRAM_BOT_TOKEN is not set in environment")
    raise SystemExit(1)

# Read current content
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Update or add TELEGRAM_BOT_TOKEN
    token_found = False
    for i, line in enumerate(lines):
        if line.startswith('TELEGRAM_BOT_TOKEN='):
            lines[i] = f'TELEGRAM_BOT_TOKEN={new_token}\n'
            token_found = True
            break
    
    if not token_found:
        lines.append(f'TELEGRAM_BOT_TOKEN={new_token}\n')
    
    # Write back
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("✓ Token updated successfully!")
else:
    print("✗ .env file not found!")
