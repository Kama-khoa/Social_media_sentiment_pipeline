import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("scripts/check_iphone_keywords.log", "r", encoding="utf-8") as f:
    lines = f.readlines()

is_prod = False
for line in lines:
    if "--- Products ---" in line:
        is_prod = True
    if is_prod and "iphone" in line.lower():
        print(line.strip())
