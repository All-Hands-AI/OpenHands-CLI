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

    def test_load_agent_with_project_skills(self, agent_store):
        """Test that loading agent includes skills from project directories."""
        # Load agent - this should include skills from both directories
        agent_store.load()

        # Verify that skills were loaded and are accessible
        skills = agent_store.load_project_skills()
        assert isinstance(skills, list)
        # Should have exactly 3 project skills: 2 microagents + 1 skill
        # (user skills may be 0 if no user skills directory exists)
        assert len(skills) >= 3

    def test_load_agent_with_user_and_project_skills_combined(self, temp_project_dir):
        """Test that user and project skills are properly combined."""
        # Create temporary user directories
        import tempfile

        with tempfile.TemporaryDirectory() as user_temp_dir:
            user_skills_temp = Path(user_temp_dir) / ".openhands" / "skills"
            user_microagents_temp = Path(user_temp_dir) / ".openhands" / "microagents"
            user_skills_temp.mkdir(parents=True)
            user_microagents_temp.mkdir(parents=True)

            # Create user skill files
            user_skill = user_skills_temp / "user_skill.md"
            user_skill.write_text("""---
name: user_skill
triggers: ["user", "skill"]
---

This is a user skill for testing.
""")

            user_microagent = user_microagents_temp / "user_microagent.md"
            user_microagent.write_text("""---
name: user_microagent
triggers: ["user", "microagent"]
---

This is a user microagent for testing.
""")

            # Mock the USER_SKILLS_DIRS constant to point to our temp directories
            mock_user_dirs = [user_skills_temp, user_microagents_temp]

            with patch(
                "openhands.sdk.context.skills.skill.USER_SKILLS_DIRS", mock_user_dirs
            ):
                with patch(
                    "openhands_cli.tui.settings.store.WORK_DIR", temp_project_dir
                ):
                    agent_store = AgentStore()
                    agent_store.load()

                    # Verify that both user and project skills were loaded
                    skills = agent_store.load_project_skills()
                    assert isinstance(skills, list)
                    # Should have 5 total skills:
                    # - 2 user skills (1 skill + 1 microagent)
                    # - 3 project skills (2 microagents + 1 skill)
                    assert len(skills) == 5
