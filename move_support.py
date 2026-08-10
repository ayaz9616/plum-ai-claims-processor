import os

moves = {
    'backend/identity.py': 'backend/app/core/identity.py',
    'backend/storage.py': 'backend/app/infrastructure/storage.py',
    'backend/trace.py': 'backend/app/trace.py',
    'backend/adapter.py': 'backend/app/core/adapter.py',
    'backend/config.py': 'backend/app/config.py'
}

for src, dst in moves.items():
    if os.path.exists(src):
        os.rename(src, dst)

files_to_update = [
    'backend/app/core/identity.py',
    'backend/app/infrastructure/storage.py',
    'backend/app/trace.py',
    'backend/app/core/adapter.py',
    'backend/app/config.py',
    'backend/app/infrastructure/providers.py',
    'backend/app/core/policy.py',
    'backend/app/agents/fraud.py',
    'backend/main.py',
    'backend/workflow.py',
    'backend/workflow_backup.py',
    'backend/orchestrator.py',
    'tests/test_config.py',
    'tests/test_ocr.py',
    'tests/test_uploads.py',
    'tests/test_extraction_normalize.py',
    'tests/test_claim_state_regression.py',
    'tests/test_workflow_p0.py'
]

replacements = {
    'from backend.identity import': 'from backend.app.core.identity import',
    'from .identity import': 'from backend.app.core.identity import',
    'from backend.storage import': 'from backend.app.infrastructure.storage import',
    'from .storage import': 'from backend.app.infrastructure.storage import',
    'from backend.trace import': 'from backend.app.trace import',
    'from .trace import': 'from backend.app.trace import',
    'from backend.adapter import': 'from backend.app.core.adapter import',
    'from .adapter import': 'from backend.app.core.adapter import',
    'from backend.config import': 'from backend.app.config import',
    'from .config import': 'from backend.app.config import'
}

for file_path in files_to_update:
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for old, new in replacements.items():
            content = content.replace(old, new)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
