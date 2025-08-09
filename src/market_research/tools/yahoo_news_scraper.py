import logging
from typing import Optional, Type

from bs4 import BeautifulSoup, Tag
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from market_research.utils.funcs import async_to_sync


class YahooNewsScraperInput(BaseModel):
    ticker: str = Field(
        ..., description="The stock ticker symbol to search news for (e.g., AAPL, TSLA)"
    )
    max_articles: int = Field(
        default=5, description="Maximum number of articles to scrape"
    )
    max_content_length: int = Field(
        default=1000, description="Maximum length of detailed content for each article"
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
            if self._browser is None:
                raise RuntimeError("Browser not initialized")
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
                name=("div", "h1"), class_=lambda x: x is not None and "cover-title" in str(x)
            )
            title = title_elem.get_text(strip=True) if isinstance(title_elem, Tag) else ""

            # Extract article body
            body_elem = soup.find("div", class_=lambda x: x is not None and "body" in str(x))
            article_body = body_elem.get_text(strip=True) if isinstance(body_elem, Tag) else ""

            return article_body, title

        except Exception as e:
            logging.warning(f"Error scraping detailed page {url}: {e}")
            return None, None

    async def _scrape_news_async(
        self, ticker: str, max_articles: int = 10, max_content_length: int = 500
    ) -> str:
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
                "li", class_=lambda x: x is not None and "story-item" in str(x)
            )
            logging.info(f"Found {len(articles_data)} story items")

            news_data = []

            for article in articles_data:
                if len(news_data) >= max_articles:
                    break
                
                # Ensure article is a Tag element
                if not isinstance(article, Tag):
                    continue

                try:
                    # Extract title from h3
                    title_elem = article.find("h3")
                    if not isinstance(title_elem, Tag):
                        continue
                    title = title_elem.get_text(strip=True)

                    # Extract URL
                    url_elem = article.find("a")
                    url = ""
                    if isinstance(url_elem, Tag):
                        href = url_elem.get("href")
                        if href and isinstance(href, str):
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
                            summary_elem.get_text(strip=True) if isinstance(summary_elem, Tag) else ""
                        )

                    # Extract source and published date
                    source = "Yahoo Finance"
                    published_at = "Unknown"

                    # Try multiple selectors for date/time information
                    time_selectors = [
                        "time",  # Standard time element
                        "[datetime]",  # Any element with datetime attribute
                        ".time",  # Class-based time selector
                        ".date",  # Class-based date selector
                        "[data-module='TimeAgo']",  # Yahoo-specific time module
                        "span[title]",  # Span with title attribute (often contains full date)
                    ]
                    
                    # Try each selector
                    for selector in time_selectors:
                        try:
                            time_elem = article.select_one(selector)
                            if time_elem and isinstance(time_elem, Tag):
                                # Try datetime attribute first
                                datetime_attr = time_elem.get('datetime')
                                if datetime_attr:
                                    published_at = datetime_attr
                                    break
                                
                                # Try title attribute 
                                title_attr = time_elem.get('title')
                                if title_attr:
                                    published_at = title_attr
                                    break
                                
                                # Try text content
                                text_content = time_elem.get_text(strip=True)
                                if text_content and text_content not in ['', 'Unknown']:
                                    published_at = text_content
                                    break
                        except Exception:
                            continue
                    
                    # Additional fallback: look for any text that looks like a date/time
                    if published_at == "Unknown":
                        # Look for elements containing common date patterns
                        all_text_elements = article.find_all(string=True)
                        
                        for text_elem in all_text_elements:
                            if text_elem and isinstance(text_elem, str):
                                text_lower = text_elem.lower().strip()
                                if text_lower and any(
                                    pattern in text_lower for pattern in 
                                    ['ago', 'min', 'hour', 'day', 'week', 'month', 'year', 'am', 'pm', '2024', '2023']
                                ) and len(text_elem.strip()) < 50:  # Reasonable date length
                                    published_at = text_elem.strip()
                                    break

                    # Add to results
                    news_data.append(
                        {
                            "title": title,
                            "content": detailed_content[:max_content_length] + "..."
                            if len(detailed_content) > max_content_length
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
                    # Close playwright 
                    self._playwright = None
                except Exception:
                    pass

    @async_to_sync
    async def _run(
        self, ticker: str, max_articles: int = 5, max_content_length: int = 1000
    ) -> str:
        """Synchronous wrapper for the async scrape method"""
        result = await self._scrape_news_async(ticker, max_articles, max_content_length)
        return result


def yahoo_news_scraper_tool(
    ticker: str, max_articles: int = 10, max_content_length: int = 500
) -> str:
    """Convenience function to create and run the Yahoo News Scraper tool"""
    tool = YahooNewsScraperTool()
    return tool._run(
        ticker=ticker, max_articles=max_articles, max_content_length=max_content_length
    )
