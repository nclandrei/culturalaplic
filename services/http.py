import httpx
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 3


class HttpError(Exception):
    """HTTP request failed after retries."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _is_retryable_httpx(e: BaseException) -> bool:
    """Check if httpx exception is retryable."""
    if isinstance(e, httpx.HTTPStatusError):
        return e.response.status_code in RETRYABLE_STATUS_CODES
    if isinstance(e, (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout)):
        return True
    return False


def _is_retryable_playwright(e: BaseException) -> bool:
    """Check if playwright exception is retryable."""
    return isinstance(e, (PlaywrightTimeout, TimeoutError))


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception(_is_retryable_httpx),
    reraise=True,
)
def _fetch_http(url: str) -> str:
    """Fetch page via HTTP with retry."""
    response = httpx.get(url, follow_redirects=True, timeout=30.0)
    response.raise_for_status()
    return response.text


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception(_is_retryable_playwright),
    reraise=True,
)
def _fetch_js(
    url: str,
    timeout: int,
    click_selector: str | None = None,
    click_count: int = 0,
    scroll_count: int = 0,
    scroll_item_selector: str | None = None,
) -> str:
    """Fetch JS-rendered page with retry.
    
    Args:
        url: Page URL to fetch
        timeout: Timeout in milliseconds
        click_selector: Optional selector for a "load more" button to click
        click_count: Number of times to click the button (0 = don't click)
        scroll_count: Number of times to scroll (for infinite scroll pages)
        scroll_item_selector: Optional selector to count items for scroll completion
    """
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        if click_selector and click_count > 0:
            for _ in range(click_count):
                try:
                    button = page.locator(click_selector).first
                    if button.is_visible():
                        button.click()
                        page.wait_for_timeout(2000)
                    else:
                        break
                except Exception:
                    break

        if scroll_count > 0:
            no_change_count = 0
            prev_item_count = 0
            for _ in range(scroll_count):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)
                if scroll_item_selector:
                    item_count = page.evaluate(
                        f"document.querySelectorAll('{scroll_item_selector}').length"
                    )
                    if item_count == prev_item_count:
                        no_change_count += 1
                        if no_change_count >= 3:
                            break
                    else:
                        no_change_count = 0
                        prev_item_count = item_count
                else:
                    prev_height = page.evaluate("document.body.scrollHeight")
                    page.wait_for_timeout(500)
                    new_height = page.evaluate("document.body.scrollHeight")
                    if new_height == prev_height:
                        no_change_count += 1
                        if no_change_count >= 3:
                            break
                    else:
                        no_change_count = 0

        content = page.content()
        browser.close()
        return content


def fetch_page(
    url: str,
    needs_js: bool = False,
    timeout: int = 30000,
    click_selector: str | None = None,
    click_count: int = 0,
    scroll_count: int = 0,
    scroll_item_selector: str | None = None,
) -> str:
    """Fetch a page, using Playwright for JS-heavy sites.

    Retries with exponential backoff on transient failures (429, 5xx, timeouts).
    Raises HttpError on permanent failures.
    
    Args:
        url: Page URL to fetch
        needs_js: Whether to use Playwright for JS-rendered pages
        timeout: Timeout in milliseconds
        click_selector: Optional selector for a "load more" button to click
        click_count: Number of times to click the button (0 = don't click)
        scroll_count: Number of times to scroll (for infinite scroll pages)
        scroll_item_selector: Optional selector to count items for scroll completion
    """
    if needs_js:
        try:
            return _fetch_js(
                url, timeout, click_selector, click_count, scroll_count, scroll_item_selector
            )
        except Exception as e:
            raise HttpError(f"Failed to fetch {url}: {e}") from e
    else:
        try:
            return _fetch_http(url)
        except httpx.HTTPStatusError as e:
            raise HttpError(
                f"HTTP {e.response.status_code} for {url}",
                status_code=e.response.status_code,
            ) from e
        except Exception as e:
            raise HttpError(f"Failed to fetch {url}: {e}") from e
