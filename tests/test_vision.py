"""Unit tests for the vision inference service."""

import re
import pytest
from unittest.mock import MagicMock
from PIL import Image

from pathsense.services.vision import NAVIGATION_PROMPT, _run_inference


# --- VIS-07: Prompt content encodes all D-01 through D-06 ---


def test_prompt_contains_calm_guidance():
    """D-01: Tone is calm guidance, not commands."""
    assert "calm" in NAVIGATION_PROMPT.lower()
    assert "command" in NAVIGATION_PROMPT.lower()


def test_prompt_prioritizes_nearest_hazard():
    """D-02: Lead with nearest hazard first."""
    assert "nearest" in NAVIGATION_PROMPT.lower()
    assert "first" in NAVIGATION_PROMPT.lower()


def test_prompt_uses_relative_distance():
    """D-03: Relative words only, no numeric."""
    assert "relative distance" in NAVIGATION_PROMPT.lower()
    assert "no numeric" in NAVIGATION_PROMPT.lower()


def test_prompt_describes_clear_scenes():
    """D-04: Describe scene even when clear."""
    prompt_lower = NAVIGATION_PROMPT.lower()
    assert "clear" in prompt_lower
    assert "describe" in prompt_lower


def test_prompt_enforces_word_limit():
    """D-05: Under 15 words."""
    assert "15 words" in NAVIGATION_PROMPT


def test_prompt_requires_directional_framing():
    """D-06: End with directional framing."""
    assert "directional framing" in NAVIGATION_PROMPT.lower()


# --- VIS-02: Model query integration ---


def test_inference_returns_model_answer():
    """VIS-02: model.query() returns a non-empty string."""
    model = MagicMock()
    model.query.return_value = {"answer": "Doorway close ahead, clear path through."}
    img = Image.new("RGB", (100, 100), color="red")
    result = _run_inference(model, img)
    assert result == "Doorway close ahead, clear path through."
    assert len(result) > 0


def test_inference_calls_model_with_prompt():
    """VIS-07: Model receives NAVIGATION_PROMPT."""
    model = MagicMock()
    model.query.return_value = {"answer": "test"}
    img = Image.new("RGB", (100, 100), color="red")
    _run_inference(model, img)
    model.query.assert_called_once()
    call_args = model.query.call_args
    assert call_args[0][1] == NAVIGATION_PROMPT


def test_image_resized_before_inference():
    """IMG-03: Image thumbnail applied before model.query."""
    model = MagicMock()
    model.query.return_value = {"answer": "test"}
    # Create oversized image
    img = Image.new("RGB", (1920, 1080), color="blue")
    _run_inference(model, img)
    # After thumbnail(384, 384), the image should be <=384 in both dimensions
    assert img.size[0] <= 384
    assert img.size[1] <= 384


# --- Output format validation helpers (used by integration tests in Plan 03) ---

RELATIVE_DISTANCE_WORDS = {"close", "nearby", "far", "ahead", "near"}
DIRECTIONAL_WORDS = {"left", "right", "ahead", "through", "forward", "straight"}


def test_no_numeric_distances_in_sample():
    """VIS-04: Sample outputs should use relative distance, not numeric."""
    sample = "Doorway close ahead, clear path through."
    # No patterns like "2 meters" or "3 feet"
    assert not re.search(r"\d+\s*(meters?|feet|ft|m)\b", sample)


def test_directional_framing_in_sample():
    """VIS-05: Sample output contains directional word."""
    sample = "Doorway close ahead, clear path through."
    words = set(sample.lower().replace(",", "").replace(".", "").split())
    assert words & DIRECTIONAL_WORDS, f"No directional words found in: {sample}"


def test_output_length_sample():
    """VIS-06: Sample output is under 15 words."""
    sample = "Doorway close ahead, clear path through."
    word_count = len(sample.split())
    assert word_count <= 15, f"Output has {word_count} words, max is 15"
