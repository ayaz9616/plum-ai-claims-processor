import os
from unittest.mock import patch
from backend.app.config import Config

def test_gemini_ocr_api_key_loading():
    # Test that when GEMINI_OCR_API_KEY is in the environment,
    # the Config class correctly picks it up.
    with patch.dict(os.environ, {"GEMINI_OCR_API_KEY": "test-ocr-key"}):
        test_config = Config()
        assert bool(test_config.gemini_ocr_api_key) is True
        
def test_gemini_llm_api_key_loading():
    # Test that when GEMINI_LLM_API_KEY is in the environment,
    # the Config class correctly picks it up.
    with patch.dict(os.environ, {"GEMINI_LLM_API_KEY": "test-llm-key"}):
        test_config = Config()
        assert bool(test_config.gemini_llm_api_key) is True
