import os

identity_path = 'backend/app/core/identity.py'
with open(identity_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('from backend.app.core.adapter import normalize_identity_name', '')

identity_func = '''
import re
import unicodedata

def normalize_identity_name(name: str) -> str:
    """Canonical, conservative identity comparison for OCR/document variations."""
    name = unicodedata.normalize("NFKC", str(name or ""))
    name = re.sub(r"^(mr|ms|mrs|dr)\.?\s*", "", name, flags=re.IGNORECASE)
    name = re.sub(r"[^\w\s]", " ", name.casefold())
    return " ".join(name.split())
'''

content = identity_func + '\n' + content

with open(identity_path, 'w', encoding='utf-8') as f:
    f.write(content)
