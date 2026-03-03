"""
QA Module - Context Collector

Collects runtime context for error classification.
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class PageContext:
    """Context collected from a Playwright page"""
    url: str
    title: str
    selector_exists: bool = False
    page_elements: Dict[str, Dict] = None
    screenshot_path: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "url": self.url,
            "title": self.title,
            "selector_exists": self.selector_exists,
            "page_elements": self.page_elements or {},
            "screenshot_path": self.screenshot_path,
        }


class ContextCollector:
    """
    Runtime context collector for error classification.

    Collects page state, element information, and other context
    to help distinguish code issues from system issues.
    """

    @staticmethod
    def collect_before_test(page, selector: str = "") -> Dict:
        """
        Collect context before test execution.

        Args:
            page: Playwright Page object
            selector: Optional selector to check for existence

        Returns:
            Dict with collected context
        """
        if page is None:
            return {}

        try:
            context = {
                "page_url": page.url,
                "page_title": page.title(),
                "selector_exists": ContextCollector._selector_exists(page, selector),
                "page_elements": ContextCollector._extract_elements(page),
            }
            return context
        except Exception as e:
            return {
                "error": str(e),
                "selector_exists": False,
            }

    @staticmethod
    def collect_on_error(page, selector: str = "") -> Dict:
        """
        Collect additional context when an error occurs.

        Args:
            page: Playwright Page object
            selector: Selector that caused the error (if any)

        Returns:
            Dict with error context
        """
        if page is None:
            return {}

        try:
            context = {
                "page_url": page.url,
                "page_title": page.title(),
                "screenshot_taken": False,
                "console_logs": ContextCollector._get_console_logs(page),
            }

            # Check for the problematic selector
            if selector:
                context["selector_exists"] = ContextCollector._selector_exists(page, selector)
                context["similar_selectors"] = ContextCollector._find_similar_selectors(
                    page, selector
                )

            return context
        except Exception as e:
            return {
                "error": str(e),
            }

    @staticmethod
    def _selector_exists(page, selector: str) -> bool:
        """
        Check if a selector exists on the page.

        Args:
            page: Playwright Page object
            selector: CSS selector to check

        Returns:
            True if selector exists, False otherwise
        """
        if not selector or not page:
            return False

        try:
            locator = page.locator(selector)
            count = locator.count()
            return count > 0
        except Exception:
            return False

    @staticmethod
    def _extract_elements(page) -> Dict[str, Dict]:
        """
        Extract interactive elements from the page.

        Args:
            page: Playwright Page object

        Returns:
            Dict mapping selectors to element info
        """
        elements = {}

        try:
            # Extract elements with data-testid (most stable)
            testid_elements = page.locator("[data-testid]").all()
            for el in testid_elements:
                try:
                    tid = el.get_attribute("data-testid")
                    if tid:
                        selector = f"[data-testid='{tid}']"
                        elements[selector] = {
                            "tag": el.evaluate("el => el.tagName"),
                            "text": el.evaluate("el => el.textContent?.trim().substring(0, 50) || ''"),
                            "visible": el.is_visible(),
                        }
                except Exception:
                    pass

            # Extract elements with id
            id_elements = page.locator("[id]").all()
            for el in id_elements[:50]:  # Limit to 50 elements
                try:
                    eid = el.get_attribute("id")
                    if eid and eid not in elements:
                        selector = f"#{eid}"
                        elements[selector] = {
                            "tag": el.evaluate("el => el.tagName"),
                            "text": el.evaluate("el => el.textContent?.trim().substring(0, 50) || ''"),
                            "visible": el.is_visible(),
                        }
                except Exception:
                    pass

        except Exception:
            pass

        return elements

    @staticmethod
    def _find_similar_selectors(page, selector: str) -> List[str]:
        """
        Find selectors similar to the given one.

        Args:
            page: Playwright Page object
            selector: CSS selector to find alternatives for

        Returns:
            List of similar selectors
        """
        similar = []

        try:
            # If looking for data-testid, return all data-testids
            if "data-testid" in selector:
                testids = page.locator("[data-testid]").all()
                for el in testids[:10]:  # Limit to 10
                    try:
                        tid = el.get_attribute("data-testid")
                        if tid:
                            similar.append(f"[data-testid='{tid}']")
                    except Exception:
                        pass

            # If looking by id, return all ids
            elif selector.startswith("#"):
                id_elements = page.locator("[id]").all()
                for el in id_elements[:10]:
                    try:
                        eid = el.get_attribute("id")
                        if eid:
                            similar.append(f"#{eid}")
                    except Exception:
                        pass

        except Exception:
            pass

        return similar

    @staticmethod
    def _get_console_logs(page) -> List[Dict]:
        """
        Get console logs from the page.

        Args:
            page: Playwright Page object

        Returns:
            List of console log entries
        """
        # Note: This requires console logging to be enabled in context
        # Implementation depends on playwright configuration
        try:
            # This would need page.on("console") handler set up beforehand
            # For now, return empty list
            return []
        except Exception:
            return []

    @staticmethod
    def capture_screenshot(page, path: str) -> bool:
        """
        Capture a screenshot of the current page.

        Args:
            page: Playwright Page object
            path: Path to save screenshot

        Returns:
            True if successful, False otherwise
        """
        if not page or not path:
            return False

        try:
            page.screenshot(path=path, full_page=False)
            return True
        except Exception:
            return False

    @staticmethod
    def get_page_state(page) -> Dict[str, Any]:
        """
        Get complete page state for debugging.

        Args:
            page: Playwright Page object

        Returns:
            Dict with page state
        """
        if not page:
            return {}

        try:
            return {
                "url": page.url,
                "title": page.title(),
                "viewport": page.viewport_size,
            }
        except Exception:
            return {}
