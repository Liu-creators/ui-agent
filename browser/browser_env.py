"""
Browser Environment - Playwright wrapper for UI Agent

Provides a clean async interface over Playwright for:
- Navigation
- Clicking / Typing / Scrolling
- Screenshots
- DOM extraction
"""

import asyncio
import base64
import os
from typing import Optional, Tuple, Any
from playwright.async_api import async_playwright, Browser, Page, Playwright


class BrowserEnv:
    """Async browser environment backed by Playwright."""

    def __init__(
        self,
        headless: bool = False,
        timeout: int = 30000,
        slow_mo: int = 0,
        save_screenshots: bool = False,
        screenshot_dir: str = "./screenshots",
    ):
        self.headless = headless
        self.timeout = timeout
        self.slow_mo = slow_mo
        self.save_screenshots = save_screenshots
        self.screenshot_dir = screenshot_dir
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._step = 0

    async def start(self):
        """Launch browser."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        self._page = await self._browser.new_page()
        self._page.set_default_timeout(self.timeout)
        if self.save_screenshots:
            os.makedirs(self.screenshot_dir, exist_ok=True)

    async def close(self):
        """Close browser."""
        if self._page:
            await self._page.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    @property
    def page(self) -> Page:
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._page

    # ---- Actions ----

    async def navigate(self, url: str) -> str:
        """Navigate to URL. Returns page title."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        await self.page.goto(url, wait_until="domcontentloaded")
        return await self.page.title()

    async def click(self, selector: str = None, coordinate: list = None) -> str:
        """Click element by CSS selector or coordinate."""
        if coordinate:
            x, y = coordinate[0], coordinate[1]
            await self.page.mouse.click(x, y)
            return f"Clicked at ({x}, {y})"
        elif selector:
            await self.page.click(selector)
            return f"Clicked '{selector}'"
        else:
            raise ValueError("Must provide either selector or coordinate")

    async def type_text(self, selector: str, text: str) -> str:
        """Clear field and type text."""
        await self.page.fill(selector, "")
        await self.page.fill(selector, text)
        return f"Typed '{text}' into '{selector}'"

    async def press_key(self, key: str) -> str:
        """Press a keyboard key."""
        await self.page.keyboard.press(key)
        return f"Pressed key: {key}"

    async def scroll(self, direction: str = "down", amount: int = 300) -> str:
        """Scroll the page."""
        dy = amount if direction == "down" else -amount
        await self.page.evaluate(f"window.scrollBy(0, {dy})")
        return f"Scrolled {direction} by {amount}px"

    async def wait(self, seconds: float = 2.0) -> str:
        """Wait for specified seconds."""
        await asyncio.sleep(seconds)
        return f"Waited {seconds}s"

    async def go_back(self) -> str:
        """Browser back button."""
        await self.page.go_back(wait_until="domcontentloaded")
        return f"Navigated back to: {self.page.url}"

    # ---- Observation ----

    async def screenshot(self) -> Tuple[str, str]:
        """
        Take screenshot. Returns (base64_str, file_path_or_empty).
        """
        self._step += 1
        screenshot_bytes = await self.page.screenshot(full_page=False)
        b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
        path = ""
        if self.save_screenshots:
            path = os.path.join(self.screenshot_dir, f"step_{self._step:04d}.png")
            with open(path, "wb") as f:
                f.write(screenshot_bytes)
        return b64, path

    async def get_dom_text(self, selector: str = None, max_chars: int = 4000) -> str:
        """
        Extract visible text from the page or specific element.
        Truncates to max_chars to fit LLM context window.
        """
        if selector:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                else:
                    text = f"No element found for selector: {selector}"
            except Exception as e:
                text = f"Error extracting element: {e}"
        else:
            # Get simplified DOM structure
            text = await self.page.evaluate("""
                () => {
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_TEXT,
                        null
                    );
                    const texts = [];
                    let node;
                    while (node = walker.nextNode()) {
                        const t = node.textContent.trim();
                        if (t.length > 0) texts.push(t);
                    }
                    return texts.join(' | ');
                }
            """)
        return text[:max_chars] if len(text) > max_chars else text

    async def get_interactive_elements(self) -> str:
        """
        Get a list of interactive elements (links, buttons, inputs) with their selectors.
        Useful for helping the agent identify clickable elements.
        """
        elements = await self.page.evaluate("""
            () => {
                const results = [];
                const selectors = 'a, button, input, select, textarea, [role="button"], [role="link"]';
                const nodes = document.querySelectorAll(selectors);
                nodes.forEach((el, i) => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        results.push({
                            index: i,
                            tag: el.tagName.toLowerCase(),
                            text: (el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || '').trim().substring(0, 50),
                            type: el.getAttribute('type') || '',
                            id: el.id || '',
                            name: el.getAttribute('name') || '',
                            href: el.href || '',
                        });
                    }
                });
                return results.slice(0, 30);  // limit to 30 elements
            }
        """)
        lines = []
        for el in elements:
            desc = f"[{el['tag']}]"
            if el['id']:
                desc += f" #{el['id']}"
            if el['name']:
                desc += f" name={el['name']}"
            if el['text']:
                desc += f" '{el['text'][:40]}'"
            lines.append(desc)
        return "\n".join(lines) if lines else "No interactive elements found"

    async def get_page_info(self) -> dict:
        """Return current page URL and title."""
        return {
            "url": self.page.url,
            "title": await self.page.title(),
        }
