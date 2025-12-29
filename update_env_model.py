
import os

def update_env_file():
    env_path = '.env'
    target_key = 'GEMINI_MODEL'
    new_value = 'gemma-3-12b'
    
    if not os.path.exists(env_path):
        print(f"{env_path} not found.")
        return

    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        found = False
        for line in lines:
            if line.strip().startswith(f'{target_key}='):
                print(f"Current value: {line.strip()}")
                new_lines.append(f'{target_key}={new_value}\n')
                found = True
            else:
                new_lines.append(line)
        
        if not found:
            print(f"Key {target_key} not found, adding it.")
            new_lines.append(f'{target_key}={new_value}\n')
            
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
            
        print(f"Updated {target_key} to {new_value} in {env_path}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_env_file()
