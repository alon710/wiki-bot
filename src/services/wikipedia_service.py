import random
from typing import Optional, Dict, Any
import wikipedia
import wikipediaapi
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class UnsuitableArticleError(Exception):
    """Raised when a Wikipedia article is not suitable for daily facts."""

    pass


class WikipediaService:
    """Service for fetching Wikipedia articles."""

    def __init__(self):
        """Initialize Hebrew Wikipedia API client."""
        self.client = wikipediaapi.Wikipedia(
            language="he",
            user_agent=settings.wikipedia.user_agent,
            timeout=settings.wikipedia.timeout,
        )

        wikipedia.set_lang("he")
        logger.info("Hebrew Wikipedia service initialized")

    def get_random_hebrew_article(
        self, max_retries: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Get a random Hebrew Wikipedia article.

        Args:
            max_retries: Maximum number of retries if articles are unsuitable

        Returns:
            Dictionary with article data or None if no suitable article found
        """
        try:
            return self._fetch_random_article_with_retry()
        except Exception as e:
            logger.error(
                "Failed to fetch suitable random Hebrew article after retries",
                max_retries=max_retries,
                error=str(e),
            )
            return None

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(UnsuitableArticleError),
    )
    def _fetch_random_article_with_retry(self) -> Dict[str, Any]:
        """
        Internal method that uses Tenacity for retrying when articles are unsuitable.

        Returns:
            Dictionary with article data

        Raises:
            UnsuitableArticleError: When article is not suitable (triggers retry)
            Exception: For other errors that should not be retried
        """
        try:
            random_title = wikipedia.random()

            actual_page = self.client.page(random_title)

            if actual_page.exists():
                if self._is_suitable_hebrew_article(actual_page):
                    article_data = {
                        "title": actual_page.title,
                        "url": actual_page.fullurl,
                        "summary": actual_page.summary[:500],
                        "full_text": actual_page.text[:2000]
                        if actual_page.text
                        else actual_page.summary,
                        "language": "he",
                    }

                    logger.info(
                        "Random Hebrew article fetched successfully",
                        title=actual_page.title,
                    )

                    return article_data
                else:
                    logger.debug(
                        "Article not suitable, retrying", title=actual_page.title
                    )
                    raise UnsuitableArticleError(
                        f"Article '{actual_page.title}' is not suitable"
                    )
            else:
                logger.debug("Page does not exist, retrying", title=random_title)
                raise UnsuitableArticleError(f"Page '{random_title}' does not exist")

        except UnsuitableArticleError:
            raise
        except Exception as e:
            if hasattr(e, "options"):
                options = getattr(e, "options", None)
                if options and len(options) > 0:
                    try:
                        random_option = random.choice(options)
                        disambig_page = self.client.page(random_option)

                        if self._is_suitable_hebrew_article(disambig_page):
                            article_data = {
                                "title": disambig_page.title,
                                "url": disambig_page.fullurl,
                                "summary": disambig_page.summary[:500],
                                "full_text": disambig_page.text[:2000]
                                if disambig_page.text
                                else disambig_page.summary,
                                "language": "he",
                            }

                            logger.info(
                                "Hebrew disambiguation article fetched successfully",
                                title=disambig_page.title,
                            )

                            return article_data
                        else:
                            logger.debug(
                                "Hebrew disambiguation article not suitable, retrying",
                                title=disambig_page.title,
                            )
                            raise UnsuitableArticleError(
                                f"Disambiguation article '{disambig_page.title}' is not suitable"
                            )
                    except UnsuitableArticleError:
                        raise
                    except Exception as disambig_error:
                        logger.warning(
                            "Error handling Hebrew disambiguation page",
                            error=str(disambig_error),
                        )
                        raise UnsuitableArticleError(
                            "Error processing disambiguation page"
                        )

            logger.warning(
                "Error fetching random Hebrew article, will retry", error=str(e)
            )
            raise UnsuitableArticleError(f"Error fetching article: {str(e)}")

    def _is_suitable_hebrew_article(self, page: wikipediaapi.WikipediaPage) -> bool:
        """
        Check if a Hebrew Wikipedia article is suitable for daily facts.

        Args:
            page: Wikipedia page to check

        Returns:
            True if the article is suitable, False otherwise
        """
        if not page.exists():
            return False

        title = page.title.lower()
        summary = (page.summary or "").lower()

        if "disambiguation" in title or "disambig" in title:
            return False

        meta_keywords = [
            "wikipedia:",
            "category:",
            "template:",
            "file:",
            "help:",
            "portal:",
            "user:",
            "talk:",
            "special:",
            "media:",
            "list of",
            "lists of",
        ]

        if any(keyword in title for keyword in meta_keywords):
            return False

        min_summary_length = 100
        if len(summary) < min_summary_length:
            return False

        if len(page.text or "") < 200:
            return False

        hebrew_chars = sum(1 for char in summary if "\u0590" <= char <= "\u05ff")
        if hebrew_chars < len(summary) * 0.3:
            return False

        logger.debug(
            "Hebrew article validation passed",
            title=page.title,
            summary_length=len(summary),
        )

        return True

    def get_hebrew_page_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific Hebrew Wikipedia page by title.

        Args:
            title: Page title

        Returns:
            Dictionary with article data or None if not found
        """
        try:
            page = self.client.page(title)

            if not page.exists():
                logger.warning("Hebrew page not found", title=title)
                return None

            article_data = {
                "title": page.title,
                "url": page.fullurl,
                "summary": page.summary[:500],
                "full_text": page.text[:2000] if page.text else page.summary,
                "language": "he",
            }

            logger.info("Hebrew page fetched by title", title=title)

            return article_data

        except Exception as e:
            logger.error(
                "Error fetching Hebrew page by title", title=title, error=str(e)
            )
            return None


wikipedia_service = WikipediaService()
