path = r'd:\Nova ai\frontend\script.js'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

opened = 0
for i, line in enumerate(lines):
    for char in line:
        if char == '{':
            opened += 1
        elif char == '}':
            opened -= 1
            if opened < 0:
                print(f"Brace mismatch! Extra '}}' found at line {i+1}:\n{line}")
                opened = 0 # reset to keep parsing

if opened > 0:
    print(f"Missing {opened} closing braces at EOF.")
elif opened == 0:
    print("Braces are balanced globally.")
