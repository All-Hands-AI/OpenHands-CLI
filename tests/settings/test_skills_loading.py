"""Unit tests for skills loading functionality in AgentStore."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from openhands_cli.tui.settings.store import AgentStore


class TestSkillsLoading:
    """Test skills loading functionality."""

    def test_load_skills_empty_directories(self):
        """Test loading skills when no skills directories exist."""
        with patch(
            "openhands_cli.tui.settings.store.load_user_skills"
        ) as mock_user_skills:
            mock_user_skills.return_value = []

            with patch("openhands_cli.tui.settings.store.WORK_DIR", "/nonexistent"):
                agent_store = AgentStore()
                skills = agent_store.load_skills()

                assert skills == []
                mock_user_skills.assert_called_once()

    def test_load_skills_user_skills_only(self):
        """Test loading user skills only."""
        mock_skill = Mock()
        mock_skill.name = "test_user_skill"

        with patch(
            "openhands_cli.tui.settings.store.load_user_skills"
        ) as mock_user_skills:
            mock_user_skills.return_value = [mock_skill]

            with patch("openhands_cli.tui.settings.store.WORK_DIR", "/nonexistent"):
                agent_store = AgentStore()
                skills = agent_store.load_skills()

                assert len(skills) == 1
                assert skills[0].name == "test_user_skill"

    def test_load_skills_project_skills_only(self):
        """Test loading project skills only."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create project skills directory
            skills_dir = Path(temp_dir) / ".openhands" / "skills"
            skills_dir.mkdir(parents=True)

            mock_repo_skill = Mock()
            mock_repo_skill.name = "repo_skill"
            mock_knowledge_skill = Mock()
            mock_knowledge_skill.name = "knowledge_skill"

            with patch(
                "openhands_cli.tui.settings.store.load_user_skills"
            ) as mock_user_skills:
                mock_user_skills.return_value = []

                with patch(
                    "openhands_cli.tui.settings.store.load_skills_from_dir"
                ) as mock_load_dir:
                    mock_load_dir.return_value = (
                        {"repo": mock_repo_skill},
                        {"knowledge": mock_knowledge_skill},
                    )

                    with patch("openhands_cli.tui.settings.store.WORK_DIR", temp_dir):
                        agent_store = AgentStore()
                        skills = agent_store.load_skills()

                        assert len(skills) == 2
                        skill_names = [skill.name for skill in skills]
                        assert "repo_skill" in skill_names
                        assert "knowledge_skill" in skill_names

    def test_load_skills_legacy_microagents(self):
        """Test loading legacy microagents from project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create both skills and microagents directories
            skills_dir = Path(temp_dir) / ".openhands" / "skills"
            microagents_dir = Path(temp_dir) / ".openhands" / "microagents"
            skills_dir.mkdir(parents=True)
            microagents_dir.mkdir(parents=True)

            mock_legacy_skill = Mock()
            mock_legacy_skill.name = "legacy_skill"

            with patch(
                "openhands_cli.tui.settings.store.load_user_skills"
            ) as mock_user_skills:
                mock_user_skills.return_value = []

                with patch(
                    "openhands_cli.tui.settings.store.load_skills_from_dir"
                ) as mock_load_dir:
                    # First call (skills dir) returns empty, second call (microagents dir) returns skill
                    mock_load_dir.side_effect = [
                        ({}, {}),  # skills directory - empty
                        (
                            {"legacy": mock_legacy_skill},
                            {},
                        ),  # microagents directory - has skill
                    ]

                    with patch("openhands_cli.tui.settings.store.WORK_DIR", temp_dir):
                        agent_store = AgentStore()
                        skills = agent_store.load_skills()

                        assert len(skills) == 1
                        assert skills[0].name == "legacy_skill"
                        # Verify both skills and microagents directories were checked
                        assert mock_load_dir.call_count == 2

    def test_load_skills_mixed_sources(self):
        """Test loading skills from multiple sources."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create both skills and microagents directories
            skills_dir = Path(temp_dir) / ".openhands" / "skills"
            microagents_dir = Path(temp_dir) / ".openhands" / "microagents"
            skills_dir.mkdir(parents=True)
            microagents_dir.mkdir(parents=True)

            # Mock user skills
            mock_user_skill = Mock()
            mock_user_skill.name = "user_skill"

            # Mock project skills
            mock_project_skill = Mock()
            mock_project_skill.name = "project_skill"

            # Mock legacy microagent
            mock_legacy_skill = Mock()
            mock_legacy_skill.name = "legacy_skill"

            with patch(
                "openhands_cli.tui.settings.store.load_user_skills"
            ) as mock_user_skills:
                mock_user_skills.return_value = [mock_user_skill]

                with patch(
                    "openhands_cli.tui.settings.store.load_skills_from_dir"
                ) as mock_load_dir:
                    # First call for skills dir, second call for microagents dir
                    mock_load_dir.side_effect = [
                        ({}, {"project": mock_project_skill}),  # skills directory
                        ({"legacy": mock_legacy_skill}, {}),  # microagents directory
                    ]

                    with patch("openhands_cli.tui.settings.store.WORK_DIR", temp_dir):
                        agent_store = AgentStore()
                        skills = agent_store.load_skills()

                        assert len(skills) == 3
                        skill_names = [skill.name for skill in skills]
                        assert "user_skill" in skill_names
                        assert "project_skill" in skill_names
                        assert "legacy_skill" in skill_names

    def test_load_skills_error_handling(self):
        """Test error handling during skills loading."""
        with patch(
            "openhands_cli.tui.settings.store.load_user_skills"
        ) as mock_user_skills:
            mock_user_skills.side_effect = Exception("User skills error")

            with patch("openhands_cli.tui.settings.store.WORK_DIR", "/nonexistent"):
                agent_store = AgentStore()
                # Should not raise exception, should handle gracefully
                skills = agent_store.load_skills()
                assert skills == []

    def test_load_skills_project_error_handling(self):
        """Test error handling for project skills loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            skills_dir = Path(temp_dir) / ".openhands" / "skills"
            skills_dir.mkdir(parents=True)

            with patch(
                "openhands_cli.tui.settings.store.load_user_skills"
            ) as mock_user_skills:
                mock_user_skills.return_value = []

                with patch(
                    "openhands_cli.tui.settings.store.load_skills_from_dir"
                ) as mock_load_dir:
                    mock_load_dir.side_effect = Exception("Project skills error")

                    with patch("openhands_cli.tui.settings.store.WORK_DIR", temp_dir):
                        agent_store = AgentStore()
                        # Should not raise exception, should handle gracefully
                        skills = agent_store.load_skills()
                        assert skills == []

    def test_load_method_passes_skills_to_context(self):
        """Test that load method passes skills to AgentContext."""
        mock_skill = Mock()
        mock_skill.name = "test_skill"

        with patch(
            "openhands_cli.tui.settings.store.load_user_skills"
        ) as mock_user_skills:
            mock_user_skills.return_value = [mock_skill]

            with patch("openhands_cli.tui.settings.store.WORK_DIR", "/nonexistent"):
                with patch(
                    "openhands_cli.tui.settings.store.AgentContext"
                ) as mock_context:
                    agent_store = AgentStore()
                    agent_store.load()

                    # Verify AgentContext was called with skills
                    mock_context.assert_called_once()
                    call_kwargs = mock_context.call_args[1]
                    assert "skills" in call_kwargs
                    assert len(call_kwargs["skills"]) == 1
                    assert call_kwargs["skills"][0].name == "test_skill"
