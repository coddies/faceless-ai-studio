"""
Fix script.js:
1. Remove extra closing brace at line ~780 (the downloadVoiceover function)
2. Add the populateThumbnailPage fix for thumbnail-actions
"""
path = r'd:\Nova ai\frontend\script.js'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Remove extra closing brace in downloadVoiceover  
# Pattern: "    }\r\n\r\n}" should be just "    }\r\n}"
# The closing of if(btn) block has }, then blank, then extra }
old_pattern = "        }, 2000);\r\n    }\r\n\r\n}"
new_pattern = "        }, 2000);\r\n    }\r\n}"

if old_pattern in content:
    content = content.replace(old_pattern, new_pattern, 1)
    print("Fix 1: Removed extra blank line in downloadVoiceover")
else:
    print("Fix 1: Pattern not found (may already be fixed)")

# Fix 2: Add thumbnail-actions support to populateThumbnailPage
old_thumb = """function populateThumbnailPage() {
    const img = document.getElementById('thumbnail-preview-img');
    const placeholder = document.getElementById('thumbnail-placeholder');
    if (!img || !placeholder) return;
    if (fullVideoKit && fullVideoKit.thumbnail_url) {
        img.src = fullVideoKit.thumbnail_url;
        img.classList.remove('hidden');
        placeholder.classList.add('hidden');
    } else {
        img.removeAttribute('src');
        img.classList.add('hidden');
        placeholder.classList.remove('hidden');
    }
}"""

new_thumb = """function populateThumbnailPage() {
    const img = document.getElementById('thumbnail-preview-img');
    const placeholder = document.getElementById('thumbnail-placeholder');
    const actions = document.getElementById('thumbnail-actions');
    if (!img || !placeholder) return;
    if (fullVideoKit && fullVideoKit.thumbnail_url) {
        img.src = fullVideoKit.thumbnail_url;
        img.classList.remove('hidden');
        placeholder.classList.add('hidden');
        if (actions) actions.classList.remove('hidden');
    } else {
        img.removeAttribute('src');
        img.classList.add('hidden');
        placeholder.classList.remove('hidden');
        if (actions) actions.classList.add('hidden');
    }
}"""

# Normalize line endings for matching
content_lf = content.replace('\r\n', '\n')
old_thumb_lf = old_thumb.replace('\r\n', '\n')
new_thumb_lf = new_thumb.replace('\r\n', '\n')

if old_thumb_lf in content_lf:
    content_lf = content_lf.replace(old_thumb_lf, new_thumb_lf, 1)
    content = content_lf  # Write with LF, will be fine
    print("Fix 2: Updated populateThumbnailPage with thumbnail-actions support")
else:
    print("Fix 2: populateThumbnailPage pattern not found (may already be fixed)")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("All fixes applied to script.js!")
