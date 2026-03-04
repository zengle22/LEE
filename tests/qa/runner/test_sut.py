"""
Unit tests for SUT (System Under Test) configuration module
"""

import pytest
import yaml
from pathlib import Path
from lee.qa.runner.sut import (
    SUTType,
    SUTConfig,
    URLResolver,
    SUTConfigLoader,
    resolve_sut_url,
)


class TestSUTType:
    """Tests for SUTType enum"""

    def test_web_type(self):
        """Test WEB type value"""
        assert SUTType.WEB.value == "web"

    def test_api_type(self):
        """Test API type value"""
        assert SUTType.API.value == "api"

    def test_mobile_type(self):
        """Test MOBILE type value"""
        assert SUTType.MOBILE.value == "mobile"

    def test_desktop_type(self):
        """Test DESKTOP type value"""
        assert SUTType.DESKTOP.value == "desktop"

    def test_microservice_type(self):
        """Test MICROSERVICE type value"""
        assert SUTType.MICROSERVICE.value == "microservice"

    def test_unknown_type(self):
        """Test UNKNOWN type value"""
        assert SUTType.UNKNOWN.value == "unknown"


class TestSUTConfig:
    """Tests for SUTConfig"""

    def test_default_values(self):
        """Test default configuration values"""
        config = SUTConfig()
        assert config.sut_type == SUTType.WEB
        assert config.base_url == "http://localhost:3000"
        assert config.base_path == ""
        assert config.protocol == "http"
        assert config.enabled is True

    def test_from_env_local(self):
        """Test creating config from 'local' env"""
        config = SUTConfig.from_env("local")
        assert config.base_url == "http://localhost:3000"

    def test_from_env_test(self):
        """Test creating config from 'test' env"""
        config = SUTConfig.from_env("test")
        assert config.base_url == "http://localhost:3000"

    def test_from_env_staging(self):
        """Test creating config from 'staging' env"""
        config = SUTConfig.from_env("staging")
        assert config.base_url == "https://app-staging.example.com"

    def test_from_env_prod(self):
        """Test creating config from 'prod' env"""
        config = SUTConfig.from_env("prod")
        assert config.base_url == "https://app.example.com"

    def test_from_env_unknown(self):
        """Test creating config from unknown env defaults to local"""
        config = SUTConfig.from_env("unknown-env")
        assert config.base_url == "http://localhost:3000"

    def test_from_env_with_overrides(self):
        """Test creating config with overrides"""
        config = SUTConfig.from_env("staging", base_url="https://custom.example.com")
        assert config.base_url == "https://custom.example.com"

    def test_to_dict(self):
        """Test converting config to dictionary"""
        config = SUTConfig(
            sut_type=SUTType.WEB,
            name="test-config",
            base_url="https://example.com",
            base_path="/app",
        )
        data = config.to_dict()
        assert data["sut_type"] == "web"
        assert data["name"] == "test-config"
        assert data["base_url"] == "https://example.com"
        assert data["base_path"] == "/app"

    def test_from_dict(self):
        """Test creating config from dictionary"""
        data = {
            "sut_type": "api",
            "name": "api-config",
            "base_url": "https://api.example.com",
            "base_path": "/api/v1",
            "auth_type": "bearer",
        }
        config = SUTConfig.from_dict(data)
        assert config.sut_type == SUTType.API
        assert config.name == "api-config"
        assert config.base_url == "https://api.example.com"
        assert config.base_path == "/api/v1"
        assert config.auth_type == "bearer"

    def test_from_dict_unknown_type(self):
        """Test creating config from dict with unknown type"""
        data = {"sut_type": "unknown_type", "base_url": "http://test.com"}
        config = SUTConfig.from_dict(data)
        assert config.sut_type == SUTType.UNKNOWN

    def test_to_env_vars(self):
        """Test converting config to environment variables"""
        config = SUTConfig(
            sut_type=SUTType.WEB,
            base_url="https://example.com",
            base_path="/app",
            protocol="https",
            auth_type="bearer",
        )
        env_vars = config.to_env_vars()
        assert env_vars["SUT_TYPE"] == "web"
        assert env_vars["SUT_BASE_URL"] == "https://example.com"
        assert env_vars["SUT_BASE_PATH"] == "/app"
        assert env_vars["SUT_PROTOCOL"] == "https"
        assert env_vars["SUT_AUTH_TYPE"] == "bearer"

    def test_extras_field(self):
        """Test extras field for type-specific config"""
        config = SUTConfig(
            sut_type=SUTType.MOBILE,
            extras={"device_id": "emulator-5554", "platform_version": "12"}
        )
        assert config.extras["device_id"] == "emulator-5554"
        assert config.extras["platform_version"] == "12"


class TestURLResolver:
    """Tests for URLResolver"""

    def test_resolve_local_env(self):
        """Test resolving URL for local environment"""
        resolver = URLResolver()
        assert resolver.resolve("local") == "http://localhost:3000"

    def test_resolve_test_env(self):
        """Test resolving URL for test environment"""
        resolver = URLResolver()
        assert resolver.resolve("test") == "http://localhost:3000"

    def test_resolve_staging_env(self):
        """Test resolving URL for staging environment"""
        resolver = URLResolver()
        assert resolver.resolve("staging") == "https://app-staging.example.com"

    def test_resolve_prod_env(self):
        """Test resolving URL for prod environment"""
        resolver = URLResolver()
        assert resolver.resolve("prod") == "https://app.example.com"

    def test_resolve_unknown_env(self):
        """Test resolving URL for unknown environment defaults to local"""
        resolver = URLResolver()
        assert resolver.resolve("unknown") == "http://localhost:3000"

    def test_resolve_explicit_url(self):
        """Test explicit URL takes priority"""
        resolver = URLResolver()
        result = resolver.resolve("staging", explicit_url="https://explicit.example.com")
        assert result == "https://explicit.example.com"

    def test_resolve_with_config_file(self, tmp_path):
        """Test config file URL takes priority over default"""
        # Create config file
        config_file = tmp_path / "sut.yaml"
        config_file.write_text("base_url: https://from-file.example.com\n")

        resolver = URLResolver()
        result = resolver.resolve("staging", config_file=config_file)
        assert result == "https://from-file.example.com"

    def test_resolve_explicit_overrides_config_file(self, tmp_path):
        """Test explicit URL overrides config file"""
        # Create config file
        config_file = tmp_path / "sut.yaml"
        config_file.write_text("base_url: https://from-file.example.com\n")

        resolver = URLResolver()
        result = resolver.resolve(
            "staging",
            explicit_url="https://explicit.example.com",
            config_file=config_file
        )
        assert result == "https://explicit.example.com"

    def test_resolve_with_sut_config(self):
        """Test resolving URL with SUTConfig object"""
        resolver = URLResolver()
        sut_config = SUTConfig(
            base_url="https://from-sut.example.com",
            base_path="/app"
        )
        result = resolver.resolve_with_config("staging", sut_config=sut_config)
        assert result == "https://from-sut.example.com/app"

    def test_resolve_with_sut_config_no_path(self):
        """Test resolving URL with SUTConfig (no base_path)"""
        resolver = URLResolver()
        sut_config = SUTConfig(base_url="https://from-sut.example.com")
        result = resolver.resolve_with_config("staging", sut_config=sut_config)
        assert result == "https://from-sut.example.com"


class TestResolveSutUrl:
    """Tests for便捷函数 resolve_sut_url"""

    def test_convenience_function_basic(self):
        """Test basic usage of convenience function"""
        result = resolve_sut_url("staging")
        assert result == "https://app-staging.example.com"

    def test_convenience_function_with_explicit(self):
        """Test convenience function with explicit URL"""
        result = resolve_sut_url("staging", explicit_url="https://override.com")
        assert result == "https://override.com"


class TestSUTConfigLoader:
    """Tests for SUTConfigLoader"""

    def test_get_tests_dir_default(self, tmp_path):
        """Test default tests directory"""
        # No .project/dirs.yaml, should fall back to tests/
        loader = SUTConfigLoader(tmp_path)
        tests_dir = loader._get_tests_dir()
        assert tests_dir == tmp_path / "tests"

    def test_get_tests_dir_from_config(self, tmp_path):
        """Test tests directory from project config"""
        # Create .project/dirs.yaml
        project_dir = tmp_path / "myproject"
        project_dir.mkdir()
        config_dir = project_dir / ".project"
        config_dir.mkdir()

        config_file = config_dir / "dirs.yaml"
        config_file.write_text("""
version: '1.0'
project_name: myproject
directories:
  tests_dir:
    path: tests
""")

        loader = SUTConfigLoader(project_dir)
        tests_dir = loader._get_tests_dir()
        assert tests_dir == project_dir / "tests"

    def test_get_runtime_dir(self, tmp_path):
        """Test runtime directory path"""
        loader = SUTConfigLoader(tmp_path)
        runtime_dir = loader.get_runtime_dir("TR-001")
        assert runtime_dir == tmp_path / "tests" / "runtime" / "TR-001"

    def test_get_config_path(self, tmp_path):
        """Test config file path"""
        loader = SUTConfigLoader(tmp_path)
        config_path = loader.get_config_path("TR-001")
        assert config_path == tmp_path / "tests" / "runtime" / "TR-001" / "sut.yaml"

    def test_load_nonexistent(self, tmp_path):
        """Test loading non-existent config returns None"""
        loader = SUTConfigLoader(tmp_path)
        config = loader.load("TR-001")
        assert config is None

    def test_save_and_load(self, tmp_path):
        """Test saving and loading config"""
        loader = SUTConfigLoader(tmp_path)

        # Save config
        config = SUTConfig(
            sut_type=SUTType.API,
            name="test-config",
            base_url="https://api.example.com",
            base_path="/api/v1",
        )
        saved_path = loader.save("TR-001", config)
        assert saved_path.exists()

        # Load config
        loaded = loader.load("TR-001")
        assert loaded is not None
        assert loaded.sut_type == SUTType.API
        assert loaded.name == "test-config"
        assert loaded.base_url == "https://api.example.com"
        assert loaded.base_path == "/api/v1"

    def test_load_or_create_existing(self, tmp_path):
        """Test load_or_create returns existing config"""
        loader = SUTConfigLoader(tmp_path)

        # Create and save config
        config = SUTConfig(sut_type=SUTType.WEB, name="existing", base_url="https://existing.com")
        loader.save("TR-001", config)

        # load_or_create should return existing
        result = loader.load_or_create("TR-001", "staging")
        assert result.name == "existing"
        assert result.base_url == "https://existing.com"

    def test_load_or_create_new(self, tmp_path):
        """Test load_or_create creates new config"""
        loader = SUTConfigLoader(tmp_path)

        # load_or_create should create new
        result = loader.load_or_create("TR-001", "staging", base_url="https://staging.com")
        assert result.name == "TR-001-staging"
        assert result.base_url == "https://staging.com"

        # Config should be saved
        assert loader.get_config_path("TR-001").exists()
