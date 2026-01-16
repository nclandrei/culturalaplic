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
def _fetch_js(url: str, timeout: int) -> str:
    """Fetch JS-rendered page with retry."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        content = page.content()
        browser.close()
        return content


def fetch_page(url: str, needs_js: bool = False, timeout: int = 30000) -> str:
    """Fetch a page, using Playwright for JS-heavy sites.

    Retries with exponential backoff on transient failures (429, 5xx, timeouts).
    Raises HttpError on permanent failures.
    """
    if needs_js:
        try:
            return _fetch_js(url, timeout)
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
