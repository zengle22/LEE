"""
Unit tests for lee.orchestrator.core.project_config

Tests for ProjectConfig, Repository, DirectoryStructureConfig, and related functions.
"""

import os
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from lee.orchestrator.core.project_config import (
    Repository,
    ProjectConfig,
    DirectoryConfig,
    DirectoryStructureConfig,
    DEFAULT_DIRECTORY_SCHEMA,
    create_project_config,
    init_project_structure,
    check_project_structure_initialized,
    require_project_structure,
    get_project_structure,
)


# =============================================================================
# Repository Tests
# =============================================================================

class TestRepository:
    """Tests for Repository dataclass."""

    def test_repository_creation(self):
        """Test creating a repository."""
        repo = Repository(
            id="backend",
            type="git",
            path="./repos/backend",
            description="Backend service",
            branch="main"
        )
        assert repo.id == "backend"
        assert repo.type == "git"
        assert repo.path == "./repos/backend"
        assert repo.description == "Backend service"
        assert repo.branch == "main"

    def test_repository_defaults(self):
        """Test repository default values."""
        repo = Repository(id="test", path=".")
        assert repo.type == "git"
        assert repo.description == ""
        assert repo.branch == "main"

    def test_repository_exists(self, tmp_path):
        """Test Repository.exists() method."""
        # Create a test directory
        test_dir = tmp_path / "test_repo"
        test_dir.mkdir()

        repo = Repository(id="test", path=str(test_dir))
        assert repo.exists(tmp_path) is True

        # Test non-existent path
        repo2 = Repository(id="test2", path="nonexistent")
        assert repo2.exists(tmp_path) is False

    def test_repository_resolve(self, tmp_path):
        """Test Repository.resolve() method."""
        repo = Repository(id="test", path="./repos/backend")
        resolved = repo.resolve(tmp_path)
        expected = (tmp_path / "repos" / "backend").resolve()
        assert resolved == expected


# =============================================================================
# ProjectConfig Tests
# =============================================================================

class TestProjectConfigBasics:
    """Tests for ProjectConfig basic functionality."""

    def test_project_config_creation(self):
        """Test creating a project config."""
        config = ProjectConfig(
            id="test-project",
            name="Test Project",
            base_path=Path("/tmp/test"),
            repositories={},
            path_aliases={},
            metadata={}
        )
        assert config.id == "test-project"
        assert config.name == "Test Project"
        assert config.base_path == Path("/tmp/test")

    def test_builtin_aliases(self):
        """Test that builtin aliases are defined in class."""
        # BUILTIN_ALIASES is a class attribute used in load(), not __init__
        assert "@openspec" in ProjectConfig.BUILTIN_ALIASES
        assert "@output" in ProjectConfig.BUILTIN_ALIASES
        assert ProjectConfig.BUILTIN_ALIASES["@openspec"] == "./openspec"
        assert ProjectConfig.BUILTIN_ALIASES["@output"] == "./output"


class TestProjectConfigLoad:
    """Tests for ProjectConfig.load()."""

    def test_load_from_yaml(self, tmp_path):
        """Test loading project config from YAML file."""
        project_yaml = tmp_path / "project.yaml"
        data = {
            "id": "my-project",
            "name": "My Project",
            "repositories": {
                "frontend": {
                    "type": "git",
                    "path": "../frontend",
                    "description": "Frontend repo"
                }
            },
            "path_aliases": {
                "@custom": "./custom"
            }
        }
        project_yaml.write_text(yaml.dump(data), encoding='utf-8')

        config = ProjectConfig.load(str(tmp_path))
        assert config.id == "my-project"
        assert config.name == "My Project"
        assert "frontend" in config.repositories
        assert config.repositories["frontend"].path == "../frontend"
        assert "@custom" in config.path_aliases

    def test_load_with_shorthand_repo(self, tmp_path):
        """Test loading with shorthand repository format."""
        project_yaml = tmp_path / "project.yaml"
        data = {
            "id": "test",
            "name": "Test",
            "repositories": {
                "backend": "../../git/backend"
            }
        }
        project_yaml.write_text(yaml.dump(data), encoding='utf-8')

        config = ProjectConfig.load(str(tmp_path))
        assert config.repositories["backend"].path == "../../git/backend"
        assert config.repositories["backend"].type == "git"  # default

    def test_load_not_found(self):
        """Test loading when project.yaml doesn't exist."""
        config = ProjectConfig.load("/nonexistent/path")
        assert config is None

    def test_find_project_yaml(self, tmp_path):
        """Test finding project.yaml by walking up directories."""
        # Create nested structure
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)

        project_yaml = tmp_path / "project.yaml"
        project_yaml.write_text("id: test\nname: Test")

        # Should find it from nested directory
        config = ProjectConfig.load(str(nested))
        assert config is not None
        assert config.id == "test"


class TestProjectConfigResolvePath:
    """Tests for ProjectConfig.resolve_path()."""

    @pytest.fixture
    def sample_config(self, tmp_path):
        """Create a sample project config."""
        return ProjectConfig(
            id="test",
            name="Test",
            base_path=tmp_path,
            repositories={
                "backend": Repository(id="backend", path="../backend"),
                "frontend": Repository(id="frontend", path="/abs/frontend")
            },
            path_aliases={
                "@openspec": "./openspec",
                "@output": "./output",
                "@backend": "${repositories.backend.path}",
                "@custom": "./custom"
            }
        )

    def test_resolve_builtin_alias(self, sample_config, tmp_path):
        """Test resolving builtin aliases."""
        # @openspec should use context_dir
        context_dir = tmp_path / "workflow"
        context_dir.mkdir()

        resolved = sample_config.resolve_path("@openspec/test.yaml", context_dir)
        expected = str(context_dir / "openspec" / "test.yaml")
        assert resolved == expected

    def test_resolve_repo_alias(self, sample_config, tmp_path):
        """Test resolving repository alias."""
        # @backend should use project base
        resolved = sample_config.resolve_path("@backend/src/main.go")
        expected = str((tmp_path / ".." / "backend" / "src" / "main.go").resolve())
        assert resolved == expected

    def test_resolve_variable_expansion(self, sample_config):
        """Test resolving ${repositories.xxx.path} variables."""
        resolved = sample_config.resolve_path("${repositories.backend.path}/src")
        assert "../backend" in resolved or "backend" in resolved

    def test_resolve_project_variable(self, sample_config):
        """Test resolving ${project.xxx} variables."""
        resolved = sample_config.resolve_path("${project.id}")
        # Should resolve to an absolute path containing "test"
        assert "test" in resolved.lower()

        resolved = sample_config.resolve_path("${project.name}")
        # Should resolve to an absolute path containing "Test"
        assert "test" in resolved.lower()

    def test_resolve_absolute_path(self, sample_config):
        """Test that absolute paths are returned as-is."""
        resolved = sample_config.resolve_path("/absolute/path/file.txt")
        assert resolved == "/absolute/path/file.txt"

    def test_resolve_empty_path(self, sample_config):
        """Test resolving empty path."""
        resolved = sample_config.resolve_path("")
        assert resolved == ""

    def test_resolve_relative_path_without_alias(self, sample_config, tmp_path):
        """Test resolving relative path without alias."""
        resolved = sample_config.resolve_path("relative/path/file.txt")
        assert "relative/path/file.txt" in resolved


class TestProjectConfigMethods:
    """Tests for other ProjectConfig methods."""

    def test_get_repository(self, tmp_path):
        """Test get_repository method."""
        repo = Repository(id="test", path=".")
        config = ProjectConfig(
            id="test",
            name="Test",
            base_path=tmp_path,
            repositories={"test": repo}
        )
        assert config.get_repository("test") == repo
        assert config.get_repository("nonexistent") is None

    def test_check_repositories(self, tmp_path):
        """Test check_repositories method."""
        # Create one existing and one non-existent repo
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        config = ProjectConfig(
            id="test",
            name="Test",
            base_path=tmp_path,
            repositories={
                "existing": Repository(id="existing", path="existing"),
                "nonexistent": Repository(id="nonexistent", path="nonexistent")
            }
        )
        result = config.check_repositories()
        assert result["existing"] is True
        assert result["nonexistent"] is False

    def test_to_dict(self, tmp_path):
        """Test to_dict method."""
        config = ProjectConfig(
            id="test",
            name="Test",
            base_path=tmp_path,
            repositories={
                "repo1": Repository(id="repo1", path=".", description="Repo 1")
            }
        )
        data = config.to_dict()
        assert data["id"] == "test"
        assert data["name"] == "Test"
        assert "repositories" in data
        assert data["kind"] == "project"

    def test_save(self, tmp_path):
        """Test save method."""
        config = ProjectConfig(
            id="test",
            name="Test",
            base_path=tmp_path
        )
        config.save()

        saved_file = tmp_path / "project.yaml"
        assert saved_file.exists()

        # Verify content
        with open(saved_file, encoding='utf-8') as f:
            data = yaml.safe_load(f)
        assert data["id"] == "test"


# =============================================================================
# DirectoryConfig Tests
# =============================================================================

class TestDirectoryConfig:
    """Tests for DirectoryConfig dataclass."""

    def test_directory_config_creation(self):
        """Test creating a directory config."""
        config = DirectoryConfig(
            name="src_dir",
            path="src",
            description="Source code directory",
            subdirs=["components", "services"],
            structure="module",
            naming="default"
        )
        assert config.name == "src_dir"
        assert config.path == "src"
        assert config.subdirs == ["components", "services"]
        assert config.structure == "module"
        assert config.naming == "default"

    def test_directory_config_defaults(self):
        """Test default values."""
        config = DirectoryConfig(
            name="test",
            path="test",
            description="Test"
        )
        assert config.subdirs == []
        assert config.structure == "flat"
        assert config.naming == "default"
        assert config.cleanup is None


# =============================================================================
# DirectoryStructureConfig Tests
# =============================================================================

class TestDirectoryStructureConfig:
    """Tests for DirectoryStructureConfig."""

    @pytest.fixture
    def sample_structure(self, tmp_path):
        """Create a sample directory structure."""
        config = DirectoryStructureConfig(
            project_dir=tmp_path,
            version="1.0",
            initialized_at="2024-01-01T00:00:00",
            initialized_by="test",
            project_name="test_project",
            directories={
                "src_dir": DirectoryConfig(
                    name="src_dir",
                    path="src",
                    description="Source code",
                    subdirs=["components"]
                ),
                "docs_dir": DirectoryConfig(
                    name="docs_dir",
                    path="docs",
                    description="Documentation"
                )
            },
            naming_conventions={
                "source": "{module}/{file}.{ext}"
            },
            constraints={
                "strict_path_validation": True,
                "forbid_creation_outside_defined_dirs": True
            }
        )
        return config

    def test_project_content_dir(self, sample_structure, tmp_path):
        """Test project_content_dir property."""
        expected = tmp_path / "test_project"
        assert sample_structure.project_content_dir == expected

    def test_project_content_dir_no_project_name(self, tmp_path):
        """Test project_content_dir without project_name."""
        config = DirectoryStructureConfig(
            project_dir=tmp_path,
            version="1.0",
            project_name=None
        )
        assert config.project_content_dir == tmp_path

    def test_get_directory_path(self, sample_structure, tmp_path):
        """Test get_directory_path method."""
        # Other dirs go under project content dir
        docs_dir = sample_structure.get_directory_path("docs_dir")
        assert docs_dir == tmp_path / "test_project" / "docs"

        # Src dir also goes under project content dir
        src_dir = sample_structure.get_directory_path("src_dir")
        assert src_dir == tmp_path / "test_project" / "src"

    def test_get_directory_path_unknown(self, sample_structure):
        """Test get_directory_path with unknown directory."""
        with pytest.raises(ValueError, match="Unknown directory"):
            sample_structure.get_directory_path("unknown_dir")

    def test_validate_output_path_valid(self, sample_structure, tmp_path):
        """Test validate_output_path with valid path."""
        # Use absolute path within project
        docs_path = tmp_path / "test_project" / "docs" / "report.md"
        is_valid, error = sample_structure.validate_output_path(
            str(docs_path),
            "doc"
        )
        assert is_valid is True
        assert error is None

    def test_validate_output_path_outside_project(self, sample_structure):
        """Test validate_output_path with path outside project."""
        is_valid, error = sample_structure.validate_output_path(
            "/etc/passwd",
            "doc"
        )
        assert is_valid is False
        assert "outside project directory" in error.lower()

    def test_validate_output_path_forbidden(self, sample_structure):
        """Test validate_output_path with forbidden path."""
        is_valid, error = sample_structure.validate_output_path(
            "random_dir/file.txt",
            "general"
        )
        assert is_valid is False
        assert "not within any configured directory" in error.lower()

    def test_validate_output_path_strict_disabled(self, sample_structure):
        """Test validate_output_path with strict validation disabled."""
        sample_structure.constraints["strict_path_validation"] = False
        is_valid, error = sample_structure.validate_output_path(
            "anywhere/file.txt"
        )
        assert is_valid is True

    def test_get_output_path_contract(self, sample_structure, tmp_path):
        """Test get_output_path for contract type."""
        # Need to have contracts_dir in the structure
        from lee.orchestrator.core.project_config import DEFAULT_DIRECTORY_SCHEMA
        # Create a full structure with all default directories
        config = DirectoryStructureConfig(
            project_dir=tmp_path,
            version="1.0",
            project_name="test",
            directories={}
        )
        # Add all directories from schema
        for name, dir_config in DEFAULT_DIRECTORY_SCHEMA["directories"].items():
            config.directories[name] = DirectoryConfig(name=name, **dir_config)

        path = config.get_output_path(
            "contract",
            layer="domain",
            version="v1",
            name="user_contract"
        )
        assert "domain" in str(path)
        assert "v1" in str(path)
        assert "user_contract.yaml" in str(path)

    def test_get_output_path_doc(self, sample_structure):
        """Test get_output_path for doc type."""
        path = sample_structure.get_output_path(
            "doc",
            category="reports",
            title="My Report"
        )
        assert "reports" in str(path)
        assert "my-report" in str(path).lower()
        assert path.suffix == ".md"

    def test_get_output_path_source(self, sample_structure):
        """Test get_output_path for source type."""
        path = sample_structure.get_output_path(
            "source",
            module="auth",
            name="login",
            ext="py"
        )
        assert "auth" in str(path)
        assert "login.py" in str(path)

    def test_get_output_path_test(self, sample_structure, tmp_path):
        """Test get_output_path for test type."""
        # Add all default directories
        from lee.orchestrator.core.project_config import DEFAULT_DIRECTORY_SCHEMA
        for name, dir_config in DEFAULT_DIRECTORY_SCHEMA["directories"].items():
            if name not in sample_structure.directories:
                sample_structure.directories[name] = DirectoryConfig(name=name, **dir_config)

        path = sample_structure.get_output_path(
            "test",
            type="unit",
            name="user",
            ext="py"
        )
        assert "unit" in str(path)
        assert "user_test.py" in str(path)

    def test_get_output_path_workflow(self, sample_structure, tmp_path):
        """Test get_output_path for workflow type."""
        # Add workflow_dir to structure
        from lee.orchestrator.core.project_config import DEFAULT_DIRECTORY_SCHEMA
        for name, dir_config in DEFAULT_DIRECTORY_SCHEMA["directories"].items():
            if name not in sample_structure.directories:
                sample_structure.directories[name] = DirectoryConfig(name=name, **dir_config)

        path = sample_structure.get_output_path(
            "workflow",
            step_id="step_001",
            name="response"
        )
        assert ".workflow" in str(path)
        assert "step_001" in str(path)

    def test_save_and_load(self, tmp_path):
        """Test save and load cycle."""
        # Create and save
        config = DirectoryStructureConfig(
            project_dir=tmp_path,
            version="1.0",
            project_name="test",
            directories={
                "src_dir": DirectoryConfig(
                    name="src_dir",
                    path="src",
                    description="Source"
                )
            }
        )
        config.save()

        # Load
        loaded = DirectoryStructureConfig.load(tmp_path)
        assert loaded.version == "1.0"
        assert loaded.project_name == "test"
        assert "src_dir" in loaded.directories

    def test_load_not_found(self, tmp_path):
        """Test load when config doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Directory structure configuration not found"):
            DirectoryStructureConfig.load(tmp_path)


# =============================================================================
# Helper Functions Tests
# =============================================================================

class TestCreateProjectConfig:
    """Tests for create_project_config function."""

    def test_create_project_config(self, tmp_path):
        """Test creating a new project config."""
        config = create_project_config(
            project_dir=str(tmp_path),
            project_id="my-project",
            project_name="My Project",
            repositories={"backend": "../backend"}
        )

        assert config.id == "my-project"
        assert config.name == "My Project"
        assert "backend" in config.repositories
        assert "@backend" in config.path_aliases


class TestInitProjectStructure:
    """Tests for init_project_structure function."""

    def test_init_basic_structure(self, tmp_path):
        """Test basic project structure initialization."""
        config = init_project_structure(
            project_dir=tmp_path,
            project_name="test_project",
            non_interactive=True
        )

        assert config.project_name == "test_project"
        assert config.initialized_at is not None
        assert len(config.directories) > 0

        # Check directories were created
        assert (tmp_path / ".project").exists()
        assert (tmp_path / "test_project").exists()
        assert (tmp_path / "test_project" / "src").exists()
        assert (tmp_path / "test_project" / "docs").exists()

        # Check config file
        config_file = tmp_path / ".project" / "dirs.yaml"
        assert config_file.exists()

    def test_init_with_custom_schema(self, tmp_path):
        """Test initialization with custom schema."""
        custom_schema = {
            "version": "2.0",
            "directories": {
                "custom_dir": {
                    "path": "custom",
                    "description": "Custom directory",
                    "subdirs": ["sub1"]
                }
            }
        }

        config = init_project_structure(
            project_dir=tmp_path,
            project_name="test",
            config_schema=custom_schema,
            non_interactive=True
        )

        assert "custom_dir" in config.directories
        assert (tmp_path / "test" / "custom" / "sub1").exists()

    def test_init_creates_readmes(self, tmp_path):
        """Test that README files are created in directories."""
        init_project_structure(
            project_dir=tmp_path,
            project_name="test",
            non_interactive=True
        )

        # Check for README in src directory
        readme = tmp_path / "test" / "src" / "README.md"
        assert readme.exists()
        content = readme.read_text(encoding='utf-8')
        assert "Source code" in content or "src" in content

    def test_init_creates_projectignore(self, tmp_path):
        """Test that .projectignore is created."""
        init_project_structure(
            project_dir=tmp_path,
            project_name="test",
            non_interactive=True
        )

        projectignore = tmp_path / ".projectignore"
        assert projectignore.exists()
        content = projectignore.read_text(encoding='utf-8')
        assert ".DS_Store" in content or "*.pyc" in content

    def test_init_already_initialized(self, tmp_path):
        """Test initializing an already initialized project."""
        # First init
        init_project_structure(
            project_dir=tmp_path,
            project_name="test",
            non_interactive=True
        )

        # Second init should return existing config
        config = init_project_structure(
            project_dir=tmp_path,
            project_name="test",
            non_interactive=True
        )

        assert config.project_name == "test"

    def test_init_force_reinitialize(self, tmp_path):
        """Test force re-initialization."""
        # First init
        config1 = init_project_structure(
            project_dir=tmp_path,
            project_name="test1",
            non_interactive=True
        )

        # Force re-init with different name
        config2 = init_project_structure(
            project_dir=tmp_path,
            project_name="test2",
            force=True,
            non_interactive=True
        )

        assert config2.project_name == "test2"

    def test_init_project_name_sanitization(self, tmp_path):
        """Test that project names are sanitized."""
        config = init_project_structure(
            project_dir=tmp_path,
            project_name="Test/Project@Name!",
            non_interactive=True
        )

        # Should be sanitized
        assert config.project_name == "Test-Project-Name"

    def test_init_without_project_name_interactive_raises(self, tmp_path, monkeypatch):
        """Test that interactive mode requires project name."""
        # Mock input to raise error or return empty to trigger validation
        monkeypatch.setattr("builtins.input", lambda x: "")

        with pytest.raises(ValueError, match="Project name cannot be empty"):
            init_project_structure(
                project_dir=tmp_path,
                project_name=None,
                non_interactive=False
            )

    def test_init_without_project_name_non_interactive(self, tmp_path):
        """Test non-interactive mode without project name."""
        config = init_project_structure(
            project_dir=tmp_path,
            project_name=None,
            non_interactive=True
        )

        # Should use current directory
        assert config.project_name is None
        assert (tmp_path / "src").exists()


class TestCheckProjectStructure:
    """Tests for check_project_structure_initialized function."""

    def test_check_initialized(self, tmp_path):
        """Test checking an initialized project."""
        init_project_structure(
            project_dir=tmp_path,
            project_name="test",
            non_interactive=True
        )

        is_init, config = check_project_structure_initialized(tmp_path)
        assert is_init is True
        assert config is not None
        assert config.project_name == "test"

    def test_check_not_initialized(self, tmp_path):
        """Test checking a non-initialized project."""
        is_init, config = check_project_structure_initialized(tmp_path)
        assert is_init is False
        assert config is None


class TestRequireProjectStructure:
    """Tests for require_project_structure function."""

    def test_require_initialized(self, tmp_path):
        """Test requiring an initialized project."""
        init_project_structure(
            project_dir=tmp_path,
            project_name="test",
            non_interactive=True
        )

        config = require_project_structure(tmp_path)
        assert config.project_name == "test"

    def test_require_not_initialized_raises(self, tmp_path):
        """Test that requiring non-initialized project raises error."""
        with pytest.raises(RuntimeError, match="Project structure not initialized"):
            require_project_structure(tmp_path)


class TestGetProjectStructure:
    """Tests for get_project_structure function."""

    def test_get_structure(self, tmp_path):
        """Test getting project structure."""
        init_project_structure(
            project_dir=tmp_path,
            project_name="test",
            non_interactive=True
        )

        config = get_project_structure(tmp_path)
        assert config.project_name == "test"


# =============================================================================
# Integration Tests
# =============================================================================

class TestProjectConfigIntegration:
    """Integration tests for project config functionality."""

    def test_full_init_and_load_cycle(self, tmp_path):
        """Test full initialization and load cycle."""
        # Initialize
        init_project_structure(
            project_dir=tmp_path,
            project_name="my_project",
            non_interactive=True
        )

        # Load via get_project_structure
        config = get_project_structure(tmp_path)

        # Validate output paths - use absolute path
        src_path = tmp_path / "my_project" / "src" / "module.py"
        is_valid, error = config.validate_output_path(
            str(src_path),
            "source"
        )
        assert is_valid is True

        # Generate output path
        output_path = config.get_output_path(
            "doc",
            category="reports",
            title="Test Report"
        )
        assert "my_project" in str(output_path)
        assert "reports" in str(output_path)

    def test_directory_structure_constraints(self, tmp_path):
        """Test that directory structure constraints are enforced."""
        config = init_project_structure(
            project_dir=tmp_path,
            project_name="test",
            non_interactive=True
        )

        # Check that constraints are set
        assert config.constraints.get("strict_path_validation") is True
        assert config.constraints.get("forbid_creation_outside_defined_dirs") is True

        # Try to validate path outside defined dirs
        is_valid, error = config.validate_output_path(
            "random_location/file.txt"
        )
        assert is_valid is False
        assert error is not None

    def test_project_config_with_directory_structure(self, tmp_path):
        """Test ProjectConfig alongside DirectoryStructureConfig."""
        # Create both
        init_project_structure(
            project_dir=tmp_path,
            project_name="test",
            non_interactive=True
        )

        project_yaml = tmp_path / "project.yaml"
        project_yaml.write_text(yaml.dump({
            "id": "test",
            "name": "Test",
            "repositories": {
                "backend": "../backend"
            }
        }))

        # Load both
        dir_config = get_project_structure(tmp_path)
        proj_config = ProjectConfig.load(str(tmp_path))

        assert dir_config is not None
        assert proj_config is not None
        assert proj_config.repositories["backend"].path == "../backend"
