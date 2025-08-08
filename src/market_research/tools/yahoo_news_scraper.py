import logging
from typing import Optional, Type

from bs4 import BeautifulSoup
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from market_research.utils.funcs import async_to_sync


class YahooNewsScraperInput(BaseModel):
    ticker: str = Field(
        ..., description="The stock ticker symbol to search news for (e.g., AAPL, TSLA)"
    )
    max_articles: int = Field(
        default=10, description="Maximum number of articles to scrape"
    )


class YahooNewsScraperTool(BaseTool):
    name: str = "Yahoo News Scraper"
    description: str = (
        "Scrapes latest news articles from Yahoo Finance for a given stock ticker using Playwright. "
        "Returns article titles, summaries, publication dates, URLs, and sources."
    )
    args_schema: Type[BaseModel] = YahooNewsScraperInput

    def __init__(self):
        super().__init__(
            name="Yahoo News Scraper",
            description=(
                "Scrapes latest news articles from Yahoo Finance for a given stock ticker using Playwright. "
                "Returns article titles, summaries, publication dates, URLs, and sources."
            ),
        )
        self._playwright = None
        self._browser = None

    async def _setup_playwright(self):
        """Set up Playwright browser instance"""
        try:
            from playwright.async_api import async_playwright

            if not self._playwright:
                self._playwright = await async_playwright().__aenter__()

            if not self._browser:
                # Launch browser with appropriate options
                self._browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                    ],
                )
            return True
        except ImportError:
            logging.warning(
                "Playwright not available. Install with: pip install playwright"
            )
            return False
        except Exception as e:
            logging.error(f"Failed to setup Playwright: {e}")
            return False

    async def _scrape_webpage(self, url: str, wait_for: str, timeout: int = 30000):
        """Scrape a webpage using Playwright and return the HTML content"""
        try:
            page = await self._browser.new_page()

            # Set user agent to avoid bot detection
            await page.set_extra_http_headers(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            )

            # Navigate to the page
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)

            # Wait for the specific element to load
            try:
                await page.wait_for_selector(wait_for, timeout=15000)
            except Exception:
                logging.warning(f"Timeout waiting for selector: {wait_for}")

            # Get the page content
            content = await page.content()
            await page.close()

            return content

        except Exception as e:
            logging.error(f"Error scraping webpage {url}: {e}")
            return None

    async def _scrape_detailed_page(
        self, url: str
    ) -> tuple[Optional[str], Optional[str]]:
        """Scrape detailed article page and return content and title"""
        try:
            content = await self._scrape_webpage(url, "div.article", timeout=15000)
            if not content:
                return None, None

            soup = BeautifulSoup(content, "html.parser")

            # Extract title
            title_elem = soup.find(
                name=("div", "h1"), class_=lambda x: x and "cover-title" in x
            )
            title = title_elem.get_text(strip=True) if title_elem else ""

            # Extract article body
            body_elem = soup.find("div", class_=lambda x: x and "body" in x)
            article_body = body_elem.get_text(strip=True) if body_elem else ""

            return article_body, title

        except Exception as e:
            logging.warning(f"Error scraping detailed page {url}: {e}")
            return None, None

    async def _scrape_news_async(self, ticker: str, max_articles: int = 10) -> str:
        """Async method to scrape Yahoo Finance news"""
        try:
            # Clean up ticker symbol and validate
            ticker = str(ticker).upper().strip()
            if not ticker:
                return "Error: No ticker symbol provided"

            logging.info(f"Fetching news for ticker: '{ticker}' using Playwright")

            # Setup Playwright
            if not await self._setup_playwright():
                return "Error: Playwright not available. Install with: pip install playwright && playwright install"

            # Build URL and selector
            news_url = f"https://finance.yahoo.com/quote/{ticker}/latest-news/"
            wait_for = "div.news-stream"

            # Scrape the main news page
            content = await self._scrape_webpage(news_url, wait_for)
            if not content:
                return f"Failed to load news page for ticker {ticker}"

            # Parse the HTML content
            soup = BeautifulSoup(content, "html.parser")

            # Find story items using the specific selector
            articles_data = soup.find_all(
                "li", class_=lambda x: x and "story-item" in x
            )
            logging.info(f"Found {len(articles_data)} story items")

            news_data = []

            for article in articles_data:
                if len(news_data) >= max_articles:
                    break

                try:
                    # Extract title from h3
                    title_elem = article.find("h3")
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)

                    # Extract URL
                    url_elem = article.find("a")
                    url = ""
                    if url_elem and url_elem.get("href"):
                        href = url_elem.get("href")
                        if not href.startswith("http"):
                            url = f"https://finance.yahoo.com{href}"
                        else:
                            url = href

                    # Try to get detailed content
                    detailed_content = ""
                    if url:
                        detailed_content, _ = await self._scrape_detailed_page(url)

                    # Fallback to summary from main page if detailed content not available
                    if not detailed_content:
                        summary_elem = article.find("p")
                        detailed_content = (
                            summary_elem.get_text(strip=True) if summary_elem else ""
                        )

                    # Extract source and published date
                    source = "Yahoo Finance"
                    published_at = "Unknown"

                    source_date_elem = article.find(
                        "div", class_=lambda x: x and "publishing" in x
                    )
                    if source_date_elem and len(source_date_elem.contents) >= 3:
                        try:
                            source = source_date_elem.contents[0].get_text(strip=True)
                            published_at = source_date_elem.contents[2].get_text(
                                strip=True
                            )
                        except (IndexError, AttributeError):
                            # Fallback to time element
                            time_elem = source_date_elem.find("time")
                            if time_elem:
                                published_at = time_elem.get_text(strip=True)

                    # Add to results
                    news_data.append(
                        {
                            "title": title,
                            "content": detailed_content[:500] + "..."
                            if len(detailed_content) > 500
                            else detailed_content,
                            "url": url,
                            "source": source,
                            "published_at": published_at,
                        }
                    )

                    logging.info(f"Scraped article: {title[:50]}...")

                except Exception as e:
                    logging.warning(f"Error processing article: {e}")
                    continue

            if not news_data:
                return f"No news articles found for ticker {ticker}. The page loaded but contained no recognizable news content."

            # Format results
            result = f"Latest news for {ticker} from Yahoo Finance:\n\n"
            for i, article in enumerate(news_data, 1):
                result += f"{i}. **{article['title']}**\n"
                result += f"   Published: {article['published_at']}\n"
                result += f"   Source: {article['source']}\n"
                if article["content"]:
                    result += f"   Summary: {article['content'][:300]}{'...' if len(article['content']) > 300 else ''}\n"
                if article["url"]:
                    result += f"   Link: {article['url']}\n"
                result += "\n"

            return result

        except Exception as e:
            logging.error(f"Error in async scraping: {e}")
            return f"Error scraping Yahoo Finance news for ticker {ticker}: {str(e)}"
        finally:
            # Cleanup
            if self._browser:
                try:
                    await self._browser.close()
                    self._browser = None
                except Exception:
                    pass
            if self._playwright:
                try:
                    await self._playwright.__aexit__(None, None, None)
                    self._playwright = None
                except Exception:
                    pass

    @async_to_sync
    async def _run(self, ticker: str, max_articles: int = 10) -> str:
        """Synchronous wrapper for the async scrape method"""
        result = await self._scrape_news_async(ticker, max_articles)
        return result


def yahoo_news_scraper_tool(ticker: str, max_articles: int = 10) -> str:
    """Convenience function to create and run the Yahoo News Scraper tool"""
    tool = YahooNewsScraperTool()
    return tool._run(ticker=ticker, max_articles=max_articles)
