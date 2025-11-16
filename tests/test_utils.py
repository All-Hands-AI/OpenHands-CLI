"""Tests for utility functions."""

from openhands_cli.utils import should_set_litellm_extra_body


def test_should_set_litellm_extra_body_for_openhands():
    """Test that litellm_extra_body is set for openhands models."""
    assert should_set_litellm_extra_body("openhands/claude-sonnet-4-5-20250929")
    assert should_set_litellm_extra_body("openhands/gpt-5-2025-08-07")
    assert should_set_litellm_extra_body("openhands/devstral-small-2507")


def test_should_not_set_litellm_extra_body_for_other_models():
    """Test that litellm_extra_body is not set for non-openhands models."""
    assert not should_set_litellm_extra_body("gpt-4")
    assert not should_set_litellm_extra_body("anthropic/claude-3")
    assert not should_set_litellm_extra_body("openai/gpt-4")
    assert not should_set_litellm_extra_body("cerebras/llama3.1-8b")
    assert not should_set_litellm_extra_body("vllm/model")
    assert not should_set_litellm_extra_body("dummy-model")
    assert not should_set_litellm_extra_body("litellm_proxy/gpt-4")
