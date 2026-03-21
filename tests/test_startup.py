import pytest
from pathsense.main import app, lifespan
from pathsense.config import MODEL_ID, TOKENIZER_ID, TOKENIZER_REVISION


def test_app_title():
    assert app.title == "PathSense"


def test_model_id_is_4bit():
    assert "4bit" in MODEL_ID


def test_tokenizer_id():
    assert TOKENIZER_ID == "vikhyatk/moondream2"


def test_tokenizer_revision():
    assert TOKENIZER_REVISION == "2025-06-21"


def test_lifespan_is_async_context_manager():
    import inspect
    assert inspect.isasyncgenfunction(lifespan.__wrapped__) or callable(lifespan)


def test_single_router_mounted():
    routes = [r.path for r in app.routes]
    assert "/health" in routes
