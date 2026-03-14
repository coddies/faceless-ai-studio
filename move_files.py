import os
import shutil

root = r"d:\Nova ai"

# Folders to create
folders = [
    r"dev-tools",
    r"backend\services",
    r"frontend\assets"
]

for folder in folders:
    path = os.path.join(root, folder)
    os.makedirs(path, exist_ok=True)

# Files to move
files_to_move = [
    (r"frontend\check_braces.py", r"dev-tools\check_braces.py"),
    (r"frontend\fix.py", r"dev-tools\fix.py")
]

for src_rel, dest_rel in files_to_move:
    src = os.path.join(root, src_rel)
    dest = os.path.join(root, dest_rel)
    if os.path.exists(src):
        shutil.move(src, dest)
        print(f"Moved {src} to {dest}")
    else:
        print(f"File {src} does not exist.")
