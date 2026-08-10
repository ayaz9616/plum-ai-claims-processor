import ast
import os

source_file = 'backend/workflow.py'
with open(source_file, 'r', encoding='utf-8') as f:
    source = f.read()

tree = ast.parse(source)

class_map = {
    'DocumentClassifier': 'backend/app/agents/document.py',
    'DocumentQualityGate': 'backend/app/agents/document.py',
    'DocumentVerifier': 'backend/app/agents/document.py',
    'DocumentExtractor': 'backend/app/agents/extraction.py',
    'ConsistencyAgent': 'backend/app/agents/consistency.py',
    'MemberDocumentConsistencyAgent': 'backend/app/agents/consistency.py',
    'CalculationEngine': 'backend/app/core/calculation.py',
    'ConfidenceEngine': 'backend/app/core/confidence.py',
    'DecisionEngine': 'backend/app/core/decision.py',
    'MemberResolver': 'backend/app/core/identity.py'
}

imports_for_files = {
    'backend/app/agents/document.py': [
        "from typing import Dict, Any, List",
        "import json",
        "from backend.app.schemas import DocumentClassification, DocumentVerificationResult, DocumentArtifact, DocumentQualityResult",
        "from backend.app.infrastructure.providers import ProviderSet",
        "from backend.app.errors import DocumentMismatchError, DocumentUnreadableError"
    ],
    'backend/app/agents/extraction.py': [
        "from typing import Dict, Any, List",
        "import json",
        "from backend.app.schemas import DocumentExtraction, DocumentArtifact, DocumentClassification",
        "from backend.app.infrastructure.providers import ProviderSet",
        "from backend.app.errors import ExtractionError",
        "from backend.app.extraction_normalize import parse_structured_document"
    ],
    'backend/app/agents/consistency.py': [
        "from typing import Dict, Any",
        "import json",
        "from backend.app.schemas import ConsistencyResult, MemberDocumentConsistencyResult, DocumentExtraction",
        "from backend.app.infrastructure.providers import ProviderSet"
    ],
    'backend/app/core/calculation.py': [
        "from typing import Dict, Any, List",
        "from decimal import Decimal",
        "from backend.app.schemas import FinancialCalculationResult"
    ],
    'backend/app/core/confidence.py': [
        "from typing import Dict, Any",
        "from backend.app.schemas import ConfidenceResult, ClaimProcessingResult",
        "from backend.app.workflow.state import ClaimState"
    ],
    'backend/app/core/decision.py': [
        "from typing import Dict, Any",
        "from backend.app.schemas import DecisionResult, ClaimProcessingResult",
        "from backend.app.workflow.state import ClaimState"
    ],
    'backend/app/core/identity.py': [
        "from typing import Dict, Any, Optional",
        "from backend.app.schemas import MemberResolutionResult",
        "from backend.app.core.adapter import normalize_identity_name"
    ]
}

# Group nodes by target file
nodes_by_file = {v: [] for v in class_map.values()}
nodes_to_remove = []

for node in tree.body:
    if isinstance(node, ast.ClassDef) and node.name in class_map:
        target = class_map[node.name]
        nodes_by_file[target].append((node.name, ast.get_source_segment(source, node)))
        nodes_to_remove.append(node)

# Create the new files
for filepath, classes in nodes_by_file.items():
    if not classes:
        continue
    content = "\n".join(imports_for_files.get(filepath, [])) + "\n\n\n"
    for name, code in classes:
        content += code + "\n\n\n"
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# Update workflow.py
# We can't just delete the nodes easily from the string because of decorators and whitespace.
# But since we have ast.get_source_segment, we can find the exact text and replace it.
# However, replacing multiple times might be tricky if substrings overlap. 
# They are separate class defs, so replacing with empty string should be fine.
new_source = source
for node in nodes_to_remove:
    segment = ast.get_source_segment(source, node)
    new_source = new_source.replace(segment, "")

# Add imports to workflow.py
new_imports = '''
from backend.app.agents.document import DocumentClassifier, DocumentQualityGate, DocumentVerifier
from backend.app.agents.extraction import DocumentExtractor
from backend.app.agents.consistency import ConsistencyAgent, MemberDocumentConsistencyAgent
from backend.app.core.calculation import CalculationEngine
from backend.app.core.confidence import ConfidenceEngine
from backend.app.core.decision import DecisionEngine
from backend.app.core.identity import MemberResolver
'''
new_source = new_imports + new_source

with open(source_file, 'w', encoding='utf-8') as f:
    f.write(new_source)

print("Done")
