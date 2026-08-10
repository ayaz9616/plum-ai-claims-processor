import os

workflow_path = 'backend/workflow.py'
with open(workflow_path, 'r', encoding='utf-8') as f:
    content = f.read()

def extract_class(content, class_name, next_def=None):
    start = content.find(f'class {class_name}')
    if start == -1: return None
    if next_def:
        end = content.find(next_def, start)
    else:
        end = len(content)
    
    # Check if there are other class defs between start and end
    # just rudimentary parsing
    return content[start:end]

print("Ready")
