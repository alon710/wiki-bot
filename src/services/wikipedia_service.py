import random
from typing import Optional, Dict, Any
import wikipediaapi

from src.config.settings import Language, settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class WikipediaService:
    """Service for fetching Wikipedia articles."""
    
    def __init__(self):
        """Initialize Wikipedia API clients for different languages."""
        self.clients = {
            Language.ENGLISH: wikipediaapi.Wikipedia(
                language='en',
                user_agent=settings.wikipedia.user_agent,
                timeout=settings.wikipedia.timeout
            ),
            Language.HEBREW: wikipediaapi.Wikipedia(
                language='he',
                user_agent=settings.wikipedia.user_agent,
                timeout=settings.wikipedia.timeout
            )
        }
        logger.info("Wikipedia service initialized", languages=list(self.clients.keys()))
    
    def get_random_article(self, language: Language, max_retries: int = 5) -> Optional[Dict[str, Any]]:
        """
        Get a random Wikipedia article for the specified language.
        
        Args:
            language: Language to fetch the article in
            max_retries: Maximum number of retries if articles are unsuitable
        
        Returns:
            Dictionary with article data or None if no suitable article found
        """
        client = self.clients.get(language)
        if not client:
            logger.error("Wikipedia client not found", language=language)
            return None
        
        attempts = 0
        while attempts < max_retries:
            try:
                attempts += 1
                
                # Get random page
                random_page = client.page("Special:Random")
                
                # If we get a redirect, follow it
                if random_page.exists():
                    actual_page = client.page(random_page.title)
                    
                    # Validate the article
                    if self._is_suitable_article(actual_page, language):
                        article_data = {
                            "title": actual_page.title,
                            "url": actual_page.fullurl,
                            "summary": actual_page.summary[:500],  # Limit summary length
                            "full_text": actual_page.text[:2000] if actual_page.text else actual_page.summary,  # Limit full text
                            "language": language.value
                        }
                        
                        logger.info("Random article fetched successfully",
                                   language=language,
                                   title=actual_page.title,
                                   attempt=attempts)
                        
                        return article_data
                    else:
                        logger.debug("Article not suitable, retrying",
                                   language=language,
                                   title=actual_page.title,
                                   attempt=attempts)
                
            except Exception as e:
                # Handle disambiguation pages by picking a random option
                if hasattr(e, 'options'):
                    options = getattr(e, 'options', None)
                    if options and len(options) > 0:
                        try:
                            random_option = random.choice(options)
                            disambig_page = client.page(random_option)
                            
                            if self._is_suitable_article(disambig_page, language):
                                article_data = {
                                    "title": disambig_page.title,
                                    "url": disambig_page.fullurl,
                                    "summary": disambig_page.summary[:500],
                                    "full_text": disambig_page.text[:2000] if disambig_page.text else disambig_page.summary,
                                    "language": language.value
                                }
                                
                                logger.info("Disambiguation article fetched successfully",
                                           language=language,
                                           title=disambig_page.title,
                                           attempt=attempts)
                                
                                return article_data
                        except Exception as disambig_error:
                            logger.warning("Error handling disambiguation page",
                                         language=language,
                                         error=str(disambig_error),
                                         attempt=attempts)
                logger.warning("Error fetching random article",
                             language=language,
                             error=str(e),
                             attempt=attempts)
        
        logger.error("Failed to fetch suitable random article after retries",
                    language=language,
                    max_retries=max_retries)
        return None
    
    def _is_suitable_article(self, page: wikipediaapi.WikipediaPage, language: Language) -> bool:
        """
        Check if a Wikipedia article is suitable for daily facts.
        
        Args:
            page: Wikipedia page to check
            language: Language of the article
        
        Returns:
            True if the article is suitable, False otherwise
        """
        if not page.exists():
            return False
        
        title = page.title.lower()
        summary = (page.summary or "").lower()
        
        # Skip disambiguation pages
        if "disambiguation" in title or "disambig" in title:
            return False
        
        # Skip meta pages
        meta_keywords = [
            "wikipedia:", "category:", "template:", "file:", "help:", "portal:",
            "user:", "talk:", "special:", "media:", "list of", "lists of"
        ]
        
        if any(keyword in title for keyword in meta_keywords):
            return False
        
        # Require minimum content length
        min_summary_length = 100
        if len(summary) < min_summary_length:
            return False
        
        # Skip pages that are too short or just redirects
        if len(page.text or "") < 200:
            return False
        
        # Language-specific filters
        if language == Language.HEBREW:
            # Skip if summary is mostly in non-Hebrew characters
            hebrew_chars = sum(1 for char in summary if '\u0590' <= char <= '\u05FF')
            if hebrew_chars < len(summary) * 0.3:  # At least 30% Hebrew characters
                return False
        
        elif language == Language.ENGLISH:
            # Skip very technical or specialized articles
            technical_keywords = [
                "algorithm", "theorem", "equation", "formula", "chemical compound",
                "protein", "gene", "species", "taxon"
            ]
            if any(keyword in title or keyword in summary for keyword in technical_keywords):
                # Allow some technical articles but with lower probability
                if random.random() < 0.7:  # 70% chance to skip technical articles
                    return False
        
        logger.debug("Article validation passed",
                    language=language,
                    title=page.title,
                    summary_length=len(summary))
        
        return True
    
    def get_page_by_title(self, title: str, language: Language) -> Optional[Dict[str, Any]]:
        """
        Get a specific Wikipedia page by title.
        
        Args:
            title: Page title
            language: Language of the page
        
        Returns:
            Dictionary with article data or None if not found
        """
        client = self.clients.get(language)
        if not client:
            logger.error("Wikipedia client not found", language=language)
            return None
        
        try:
            page = client.page(title)
            
            if not page.exists():
                logger.warning("Page not found", title=title, language=language)
                return None
            
            article_data = {
                "title": page.title,
                "url": page.fullurl,
                "summary": page.summary[:500],
                "full_text": page.text[:2000] if page.text else page.summary,
                "language": language.value
            }
            
            logger.info("Page fetched by title",
                       language=language,
                       title=title)
            
            return article_data
            
        except Exception as e:
            logger.error("Error fetching page by title",
                        title=title,
                        language=language,
                        error=str(e))
            return None


# Global service instance
wikipedia_service = WikipediaService()