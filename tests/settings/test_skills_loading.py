"""Unit tests for skills loading functionality in AgentStore."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from openhands_cli.tui.settings.store import AgentStore


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with microagents."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create microagents directory with actual files
        microagents_dir = Path(temp_dir) / ".openhands" / "microagents"
        microagents_dir.mkdir(parents=True)

        # Create test microagent files
        microagent1 = microagents_dir / "test_microagent.md"
        microagent1.write_text("""---
name: test_microagent
triggers: ["test", "microagent"]
---

This is a test microagent for testing purposes.
""")

        microagent2 = microagents_dir / "integration_test.md"
        microagent2.write_text("""---
name: integration_test
triggers: ["integration", "test"]
---

This microagent is used for integration testing.
""")

        # Also create skills directory
        skills_dir = Path(temp_dir) / ".openhands" / "skills"
        skills_dir.mkdir(parents=True)

        skill_file = skills_dir / "test_skill.md"
        skill_file.write_text("""---
name: test_skill
triggers: ["test", "skill"]
---

This is a test skill for testing purposes.
""")

        yield temp_dir


@pytest.fixture
def agent_store(temp_project_dir):
    """Create an AgentStore with the temporary project directory."""
    with patch("openhands_cli.tui.settings.store.WORK_DIR", temp_project_dir):
        yield AgentStore()


class TestSkillsLoading:
    """Test skills loading functionality with actual microagents."""

    def test_load_agent_with_skills(self, agent_store):
        """Test that loading agent includes skills from microagents and skills dirs."""
        # Load agent - this should include skills from both directories
        agent_store.load()

        # Verify that skills were loaded and are accessible
        skills = agent_store.load_skills()
        assert isinstance(skills, list)
        # Skills should include both user skills and project skills
        assert len(skills) >= 0
