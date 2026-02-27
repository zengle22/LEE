"""
Unit tests for ContextCollector
"""

import pytest
from unittest.mock import Mock
from lee.qa.classifier.context_collector import ContextCollector


class TestContextCollector:
    """Tests for ContextCollector"""

    def test_collect_before_test_with_page(self):
        """Test context collection with valid page"""
        mock_page = Mock()
        mock_page.url = "http://localhost:3000/login"
        mock_page.title = Mock(return_value="Login Page")

        # Mock selector exists
        mock_locator = Mock()
        mock_locator.count = Mock(return_value=1)
        mock_page.locator = Mock(return_value=mock_locator)

        # Mock element extraction
        mock_page.locator = Mock(return_value=mock_locator)
        mock_locator.all = Mock(return_value=[])

        context = ContextCollector.collect_before_test(mock_page, "[data-testid='submit']")

        assert context["page_url"] == "http://localhost:3000/login"
        assert context["page_title"] == "Login Page"
        assert "selector_exists" in context
        assert "page_elements" in context

    def test_collect_before_test_without_page(self):
        """Test context collection with None page"""
        context = ContextCollector.collect_before_test(None, "")
        assert context == {}

    def test_collect_on_error(self):
        """Test context collection on error"""
        mock_page = Mock()
        mock_page.url = "http://localhost:3000/error"
        mock_page.title = Mock(return_value="Error Page")

        context = ContextCollector.collect_on_error(mock_page)

        assert context["page_url"] == "http://localhost:3000/error"
        assert "screenshot_taken" in context
        assert "console_logs" in context

    def test_selector_exists_true(self):
        """Test selector exists returns True"""
        mock_page = Mock()
        mock_locator = Mock()
        mock_locator.count = Mock(return_value=1)
        mock_page.locator = Mock(return_value=mock_locator)

        exists = ContextCollector._selector_exists(mock_page, "[data-testid='button']")
        assert exists is True

    def test_selector_exists_false(self):
        """Test selector exists returns False when count is 0"""
        mock_page = Mock()
        mock_locator = Mock()
        mock_locator.count = Mock(return_value=0)
        mock_page.locator = Mock(return_value=mock_locator)

        exists = ContextCollector._selector_exists(mock_page, "[data-testid='missing']")
        assert exists is False

    def test_selector_exists_exception(self):
        """Test selector exists returns False on exception"""
        mock_page = Mock()
        mock_page.locator = Mock(side_effect=Exception("Test error"))

        exists = ContextCollector._selector_exists(mock_page, "[data-testid='button']")
        assert exists is False

    def test_extract_elements(self):
        """Test element extraction from page"""
        mock_page = Mock()
        mock_locator = Mock()
        mock_locator.all = Mock(return_value=[])
        mock_page.locator = Mock(return_value=mock_locator)

        elements = ContextCollector._extract_elements(mock_page)
        assert isinstance(elements, dict)

    def test_find_similar_selectors(self):
        """Test finding similar selectors"""
        mock_page = Mock()
        mock_locator = Mock()
        mock_elem = Mock()
        mock_elem.get_attribute = Mock(return_value="button-1")
        mock_locator.all = Mock(return_value=[mock_elem])
        mock_page.locator = Mock(return_value=mock_locator)

        similar = ContextCollector._find_similar_selectors(mock_page, "[data-testid='button']")
        assert isinstance(similar, list)

    def test_capture_screenshot_success(self, tmp_path):
        """Test successful screenshot capture"""
        mock_page = Mock()
        mock_page.screenshot = Mock(return_value=True)

        screenshot_path = tmp_path / "test.png"
        result = ContextCollector.capture_screenshot(mock_page, str(screenshot_path))

        mock_page.screenshot.assert_called_once()
        # Result depends on actual implementation

    def test_capture_screenshot_failure(self):
        """Test screenshot capture failure"""
        mock_page = Mock()
        mock_page.screenshot = Mock(side_effect=Exception("Screenshot failed"))

        result = ContextCollector.capture_screenshot(mock_page, "/tmp/test.png")
        assert result is False

    def test_get_page_state(self):
        """Test getting page state"""
        mock_page = Mock()
        mock_page.url = "http://localhost:3000"
        mock_page.title = Mock(return_value="Test")
        mock_page.viewport_size = {"width": 1920, "height": 1080}

        state = ContextCollector.get_page_state(mock_page)

        assert state["url"] == "http://localhost:3000"
        assert "viewport" in state
