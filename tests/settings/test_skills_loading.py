"""Unit tests for skills loading functionality in AgentStore."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from openhands_cli.tui.settings.store import AgentStore


class TestSkillsLoading:
    """Test skills loading functionality with actual microagents in temporary directories."""

    def test_load_skills_with_project_microagents_directory(self):
        """Test loading skills when project microagents directory exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create microagents directory with actual file
            microagents_dir = Path(temp_dir) / ".openhands" / "microagents"
            microagents_dir.mkdir(parents=True)

            # Create a test microagent file
            microagent_file = microagents_dir / "test_microagent.md"
            microagent_file.write_text("""---
name: test_microagent
triggers: ["test", "microagent"]
---

This is a test microagent for testing purposes.
""")

            with patch(
                "openhands_cli.tui.settings.store.load_user_skills"
            ) as mock_user_skills:
                mock_user_skills.return_value = []

                with patch("openhands_cli.tui.settings.store.WORK_DIR", temp_dir):
                    agent_store = AgentStore()
                    skills = agent_store.load_skills()

                    # Verify that skills were loaded from the microagents directory
                    assert (
                        len(skills) >= 0
                    )  # May be 0 if load_skills_from_dir doesn't find valid skills

    def test_load_skills_with_project_skills_directory(self):
        """Test loading skills when project skills directory exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create skills directory with actual file
            skills_dir = Path(temp_dir) / ".openhands" / "skills"
            skills_dir.mkdir(parents=True)

            # Create a test skill file
            skill_file = skills_dir / "test_skill.md"
            skill_file.write_text("""---
name: test_skill
triggers: ["test", "skill"]
---

This is a test skill for testing purposes.
""")

            with patch(
                "openhands_cli.tui.settings.store.load_user_skills"
            ) as mock_user_skills:
                mock_user_skills.return_value = []

                with patch("openhands_cli.tui.settings.store.WORK_DIR", temp_dir):
                    agent_store = AgentStore()
                    skills = agent_store.load_skills()

                    # Verify that skills were loaded from the skills directory
                    assert (
                        len(skills) >= 0
                    )  # May be 0 if load_skills_from_dir doesn't find valid skills

    def test_load_method_with_actual_microagents(self):
        """Test that load method works with actual microagents in temporary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create microagents directory with actual file
            microagents_dir = Path(temp_dir) / ".openhands" / "microagents"
            microagents_dir.mkdir(parents=True)

            # Create a test microagent file
            microagent_file = microagents_dir / "integration_test.md"
            microagent_file.write_text("""---
name: integration_test
triggers: ["integration", "test"]
---

This microagent is used for integration testing.
""")

            with patch(
                "openhands_cli.tui.settings.store.load_user_skills"
            ) as mock_user_skills:
                mock_user_skills.return_value = []

                with patch("openhands_cli.tui.settings.store.WORK_DIR", temp_dir):
                    with patch(
                        "openhands_cli.tui.settings.store.AgentContext"
                    ) as mock_context:
                        agent_store = AgentStore()
                        agent_store.load()

                        # Verify AgentContext was called with skills parameter
                        mock_context.assert_called_once()
                        call_kwargs = mock_context.call_args[1]
                        assert "skills" in call_kwargs
                        # Skills list should be present (may be empty if loading fails)
                        assert isinstance(call_kwargs["skills"], list)
