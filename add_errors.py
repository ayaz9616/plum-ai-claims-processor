import os

errors_path = 'backend/app/errors.py'
with open(errors_path, 'a', encoding='utf-8') as f:
    f.write('''
class DocumentUnreadableError(PlumError):
    code = "DOCUMENT_UNREADABLE"

class DocumentMismatchError(PlumError):
    code = "DOCUMENT_MISMATCH"

class ExtractionError(PlumError):
    code = "EXTRACTION_ERROR"
''')
