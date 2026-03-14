import os

files_to_delete = [
    r"d:\Nova ai\frontend\check_braces.py",
    r"d:\Nova ai\frontend\fix.py"
]

for f in files_to_delete:
    if os.path.exists(f):
        os.remove(f)
        print(f"Deleted {f}")
