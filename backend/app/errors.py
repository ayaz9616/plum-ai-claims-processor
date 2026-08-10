from typing import Optional


class PlumError(Exception):
    code: str = "PLUM_ERROR"

    def __init__(self, message: str, code: Optional[str] = None):
        super().__init__(message)
        if code:
            self.code = code


class PolicyNotFound(PlumError):
    code = "POLICY_NOT_FOUND"


class PolicySchemaInvalid(PlumError):
    code = "POLICY_SCHEMA_INVALID"


class RepositoryError(PlumError):
    code = "REPOSITORY_ERROR"

class DocumentUnreadableError(PlumError):
    code = "DOCUMENT_UNREADABLE"

class DocumentMismatchError(PlumError):
    code = "DOCUMENT_MISMATCH"

class ExtractionError(PlumError):
    code = "EXTRACTION_ERROR"
