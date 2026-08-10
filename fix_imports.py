import os

replacements = {
    'from backend.schemas import': 'from backend.app.schemas import',
    'from .schemas import': 'from .app.schemas import',
    'from backend.errors import': 'from backend.app.errors import',
    'from .errors import': 'from .app.errors import',
}

files = [
    'tests/test_fraud.py',
    'backend/workflow.py',
    'backend/workflow_backup.py',
    'backend/trace.py',
    'backend/policy_evaluator.py',
    'backend/policy.py',
    'backend/orchestrator.py',
    'backend/main.py',
    'backend/fraud_analyzer.py',
    'backend/extraction_normalize.py',
    'backend/uploads.py'
]

for file_path in files:
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for old, new in replacements.items():
            content = content.replace(old, new)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
