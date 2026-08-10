import os

repo_path = 'backend/app/infrastructure/repositories.py'
fraud_path = 'backend/fraud_analyzer.py'
new_fraud_path = 'backend/app/agents/fraud.py'

# 1. Append to repositories.py
with open(repo_path, 'r', encoding='utf-8') as f:
    repo_content = f.read()

if 'from typing import' not in repo_content:
    repo_content = 'from typing import Dict, Any, List\n' + repo_content

claim_repo_code = '''
class ClaimHistoryRepository:
    def __init__(self):
        self._db = {
            "EMP008": [
                {"claim_id": "CLM_0081", "date": "2024-10-30", "amount": 1200, "provider": "City Clinic A"},
                {"claim_id": "CLM_0082", "date": "2024-10-30", "amount": 1800, "provider": "City Clinic B"},
                {"claim_id": "CLM_0083", "date": "2024-10-30", "amount": 2100, "provider": "Wellness Center"}
            ]
        }

    def get_member_claims(self, member_id: str, claim: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        # Try local seed DB first
        if member_id and member_id in self._db:
            return self._db[member_id]
            
        # Fallback to request payload
        if claim and claim.get("claims_history"):
            return claim.get("claims_history", [])
        return []
'''

with open(repo_path, 'w', encoding='utf-8') as f:
    f.write(repo_content + '\n' + claim_repo_code)

# 2. Modify and Move fraud_analyzer.py
with open(fraud_path, 'r', encoding='utf-8') as f:
    fraud_content = f.read()

import_statement = "from backend.app.infrastructure.repositories import ClaimHistoryRepository\n"
if import_statement not in fraud_content:
    fraud_content = import_statement + fraud_content

# Remove ClaimHistoryRepository from fraud_analyzer.py
# It starts at 'class ClaimHistoryRepository:' and ends before 'class FraudAnalyzer:'
start = fraud_content.find('class ClaimHistoryRepository:')
end = fraud_content.find('class FraudAnalyzer:')
if start != -1 and end != -1:
    fraud_content = fraud_content[:start] + fraud_content[end:]

with open(new_fraud_path, 'w', encoding='utf-8') as f:
    f.write(fraud_content)

os.remove(fraud_path)

# 3. Update tests/test_fraud.py
test_path = 'tests/test_fraud.py'
with open(test_path, 'r', encoding='utf-8') as f:
    test_content = f.read()
test_content = test_content.replace('from backend.fraud_analyzer import', 'from backend.app.agents.fraud import')
with open(test_path, 'w', encoding='utf-8') as f:
    f.write(test_content)

# 4. Update workflow files
workflow_files = ['backend/workflow.py', 'backend/workflow_backup.py']
for wf in workflow_files:
    if os.path.exists(wf):
        with open(wf, 'r', encoding='utf-8') as f:
            wf_content = f.read()
        wf_content = wf_content.replace('from .fraud_analyzer import', 'from backend.app.agents.fraud import')
        with open(wf, 'w', encoding='utf-8') as f:
            f.write(wf_content)
