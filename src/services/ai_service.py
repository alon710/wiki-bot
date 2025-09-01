from typing import Dict, Any, Optional
from openai import OpenAI

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AIService:
    """Service for AI-powered text summarization using OpenRouter."""
    
    def __init__(self):
        """Initialize OpenRouter client."""
        self.client = OpenAI(
            api_key=settings.openrouter.api_key,
            base_url=settings.openrouter.base_url
        )
        logger.info("AI service initialized with OpenRouter")
    
    def generate_hebrew_daily_fact(self, article_data: Dict[str, Any]) -> Optional[str]:
        """
        Generate an engaging Hebrew daily fact summary from Wikipedia article data.
        
        Args:
            article_data: Dictionary containing article title, summary, and text
        
        Returns:
            Engaging Hebrew fact summary or None if generation fails
        """
        try:
            title = article_data.get("title", "")
            content = article_data.get("full_text", article_data.get("summary", ""))
            
            if not content:
                logger.error("No content provided for summarization", title=title)
                return None
            
            # Create Hebrew summarization prompt
            prompt = self._create_hebrew_prompt(title, content)
            
            # Make API call to OpenRouter
            response = self.client.chat.completions.create(
                model=settings.openrouter.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_hebrew_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=settings.openrouter.max_tokens,
                temperature=settings.openrouter.temperature,
                top_p=0.9,
                frequency_penalty=0.1,
                presence_penalty=0.1
            )
            
            if response.choices and len(response.choices) > 0:
                summary = response.choices[0].message.content.strip()
                
                # Validate summary
                if self._validate_hebrew_summary(summary):
                    logger.info("Hebrew AI fact summary generated successfully",
                              title=title,
                              summary_length=len(summary))
                    return summary
                else:
                    logger.warning("Generated Hebrew summary failed validation",
                                 title=title)
                    return None
            
            logger.error("No response from OpenRouter", title=title)
            return None
            
        except Exception as e:
            logger.error("Failed to generate Hebrew AI summary",
                        title=article_data.get("title", ""),
                        error=str(e))
            return None
    
    def _get_hebrew_system_prompt(self) -> str:
        """Get Hebrew system prompt."""
        return (
            "אתה כותב עובדות יומיות מעניינות ומרתקות מויקיפדיה בעברית. "
            "המטרה שלך היא ליצור עובדה קצרה (2-3 משפטים) שתעורר עניין ותהיה קלה לזכירה. "
            "השתמש בשפה פשוטה וברורה, וודא שהעובדה מרתקת ומעניינת לקורא הישראלי הממוצע."
        )
    
    def _create_hebrew_prompt(self, title: str, content: str) -> str:
        """Create Hebrew summarization prompt."""
        return f"""
הכותרת: {title}

התוכן:
{content[:1500]}  

אנא צור עובדה יומית מעניינת ומרתקת בהתבסס על המידע הזה. העובדה צריכה להיות:
- באורך של 2-3 משפטים
- כתובה בעברית פשוטה וברורה
- מעניינת ומרתקת
- מדויקת למידע שסופק
- מתאימה לקהל הישראלי הרחב

העובדה היומית:
"""
    
    def _validate_hebrew_summary(self, summary: str) -> bool:
        """Validate the generated Hebrew summary."""
        if not summary or len(summary.strip()) == 0:
            return False
        
        # Check minimum and maximum length
        min_length = 50  # Minimum characters
        max_length = 400  # Maximum characters
        
        if len(summary) < min_length or len(summary) > max_length:
            logger.warning("Hebrew summary length out of bounds",
                         length=len(summary),
                         min_length=min_length,
                         max_length=max_length)
            return False
        
        # Check sentence count (should be 2-4 sentences)
        sentence_count = len([s for s in summary.split('.') if s.strip()])
        if sentence_count < 1 or sentence_count > 5:
            logger.warning("Hebrew summary sentence count out of bounds",
                         sentence_count=sentence_count)
            return False
        
        # Check if summary contains Hebrew characters
        hebrew_chars = sum(1 for char in summary if '\u0590' <= char <= '\u05FF')
        if hebrew_chars < len(summary) * 0.3:  # At least 30% Hebrew
            logger.warning("Hebrew summary contains insufficient Hebrew characters",
                         hebrew_ratio=hebrew_chars / len(summary))
            return False
        
        # Check for common AI response patterns to avoid
        avoid_patterns = [
            "I cannot", "I don't have", "I'm sorry", "As an AI",
            "אני לא יכול", "אני לא מסוגל", "אני מצטער", "כבוט AI"
        ]
        
        summary_lower = summary.lower()
        if any(pattern.lower() in summary_lower for pattern in avoid_patterns):
            logger.warning("Hebrew summary contains unwanted AI response patterns")
            return False
        
        logger.debug("Hebrew summary validation passed",
                    length=len(summary),
                    sentence_count=sentence_count)
        
        return True
    


# Global service instance
ai_service = AIService()