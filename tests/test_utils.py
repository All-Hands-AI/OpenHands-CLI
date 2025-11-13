"""Tests for utility functions."""

from openhands_cli.utils import should_set_litellm_extra_body


def test_should_set_litellm_extra_body_for_litellm_proxy():
    """Test that litellm_extra_body is set for litellm_proxy models."""
    assert should_set_litellm_extra_body("litellm_proxy/gpt-4")
    assert should_set_litellm_extra_body("litellm_proxy/claude-3")
    assert should_set_litellm_extra_body("some-provider/litellm_proxy-model")


def test_should_not_set_litellm_extra_body_for_other_models():
    """Test that litellm_extra_body is not set for non-litellm_proxy models."""
    assert not should_set_litellm_extra_body("gpt-4")
    assert not should_set_litellm_extra_body("anthropic/claude-3")
    assert not should_set_litellm_extra_body("openai/gpt-4")
    assert not should_set_litellm_extra_body("cerebras/llama3.1-8b")
    assert not should_set_litellm_extra_body("vllm/model")
    assert not should_set_litellm_extra_body("dummy-model")
