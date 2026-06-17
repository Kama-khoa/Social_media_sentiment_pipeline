import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("scripts/check_iphone_keywords.log", "r", encoding="utf-8") as f:
    lines = f.readlines()

is_keyword = True
for line in lines:
    if "--- Products ---" in line:
        is_keyword = False
    if is_keyword and "iphone 16 pro" in line.lower():
        print(line.strip())
