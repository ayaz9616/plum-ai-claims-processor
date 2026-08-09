from pathlib import Path
import os


class Config:
    def __init__(self):
        # Base directory is repo root (one level up from this package)
        self.base_dir = Path(__file__).resolve().parent.parent
        self.policy_path = Path(os.environ.get("POLICY_PATH", self.base_dir / "policy_terms.json"))
        self.app_name = os.environ.get("APP_NAME", "plum-claims-ai")
        self.environment = os.environ.get("ENVIRONMENT", "development")
        self.log_level = os.environ.get("LOG_LEVEL", "INFO")
        self.database_url = os.environ.get("DATABASE_URL", "")
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        self.gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        self.gemini_ocr_model = os.environ.get("GEMINI_OCR_MODEL", self.gemini_model)
        self.gemini_temperature = float(os.environ.get("GEMINI_TEMPERATURE", "0.0"))


config = Config()
