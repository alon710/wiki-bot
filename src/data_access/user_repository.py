from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import select

from src.models.user import User, UserCreate, UserUpdate
from src.data_access.database_client import database_client
from src.utils.logger import get_logger
from src.config.settings import Language

logger = get_logger(__name__)


class UserRepository:
    """Repository for user data operations."""
    
    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        try:
            def create_user_operation(session):
                user = User(**user_data.model_dump())
                session.add(user)
                session.commit()
                session.refresh(user)
                
                logger.info("User created successfully", phone=user.phone, language=user.language)
                return user
                
            return database_client.execute_with_retry_manual_commit(create_user_operation)
                
        except Exception as e:
            logger.error("Failed to create user", phone=user_data.phone, error=str(e))
            raise
    
    def get_user_by_phone(self, phone: str) -> Optional[User]:
        """Get user by phone number."""
        try:
            def get_user_operation(session):
                logger.debug("Executing user lookup query", phone=phone)
                statement = select(User).where(User.phone == phone)
                user_from_db = session.exec(statement).first()
                logger.debug("User lookup query completed", phone=phone, found=user_from_db is not None)
                
                if user_from_db:
                    # Create a detached copy to avoid session binding issues
                    user_copy = User(
                        id=user_from_db.id,
                        phone=user_from_db.phone,
                        language=user_from_db.language,
                        subscribed=user_from_db.subscribed,
                        last_message_at=user_from_db.last_message_at,
                        created_at=user_from_db.created_at,
                        updated_at=user_from_db.updated_at
                    )
                    logger.debug("Created detached user copy", phone=phone, user_id=user_copy.id)
                    return user_copy
                return None
                
            user = database_client.execute_with_retry(get_user_operation)
            
            if user:
                logger.debug("User found", 
                           phone=phone, 
                           user_id=user.id,
                           language=user.language,
                           subscribed=user.subscribed)
            else:
                logger.debug("User not found", phone=phone)
            
            return user
                
        except Exception as e:
            logger.error("Failed to get user by phone", 
                        phone=phone, 
                        error=str(e),
                        error_type=type(e).__name__)
            raise
    
    def update_user(self, phone: str, user_data: UserUpdate) -> Optional[User]:
        """Update user preferences."""
        try:
            def update_user_operation(session):
                statement = select(User).where(User.phone == phone)
                user = session.exec(statement).first()
                
                if not user:
                    logger.warning("User not found for update", phone=phone)
                    return None
                
                # Update only provided fields
                update_data = user_data.model_dump(exclude_unset=True)
                for field, value in update_data.items():
                    setattr(user, field, value)
                
                user.updated_at = datetime.now(timezone.utc)
                session.add(user)
                session.commit()
                session.refresh(user)
                
                logger.info("User updated successfully", phone=phone, updated_fields=list(update_data.keys()))
                return user
                
            return database_client.execute_with_retry_manual_commit(update_user_operation)
                
        except Exception as e:
            logger.error("Failed to update user", phone=phone, error=str(e))
            raise
    
    def get_subscribed_users_by_language(self, language: Language) -> List[User]:
        """Get all subscribed users for a specific language."""
        try:
            def get_users_operation(session):
                statement = select(User).where(
                    User.subscribed,
                    User.language == language
                )
                return session.exec(statement).all()
                
            users = database_client.execute_with_retry(get_users_operation)
            logger.info("Retrieved subscribed users", language=language, count=len(users))
            return users
                
        except Exception as e:
            logger.error("Failed to get subscribed users", language=language, error=str(e))
            raise
    
    def get_all_subscribed_users(self) -> List[User]:
        """Get all subscribed users."""
        try:
            def get_all_users_operation(session):
                statement = select(User).where(User.subscribed)
                return session.exec(statement).all()
                
            users = database_client.execute_with_retry(get_all_users_operation)
            logger.info("Retrieved all subscribed users", count=len(users))
            return users
                
        except Exception as e:
            logger.error("Failed to get all subscribed users", error=str(e))
            raise
    
    def delete_user(self, phone: str) -> bool:
        """Delete a user."""
        try:
            with database_client.get_session() as session:
                statement = select(User).where(User.phone == phone)
                user = session.exec(statement).first()
                
                if not user:
                    logger.warning("User not found for deletion", phone=phone)
                    return False
                
                session.delete(user)
                session.commit()
                
                logger.info("User deleted successfully", phone=phone)
                return True
                
        except Exception as e:
            logger.error("Failed to delete user", phone=phone, error=str(e))
            raise
    
    def update_last_message(self, phone: str) -> bool:
        """Update user's last message timestamp."""
        try:
            def update_timestamp_operation(session):
                statement = select(User).where(User.phone == phone)
                user = session.exec(statement).first()
                
                if user:
                    user.last_message_at = datetime.now(timezone.utc)
                    session.add(user)
                    session.commit()
                    logger.debug("User last message timestamp updated", phone=phone)
                    return True
                return False
                
            return database_client.execute_with_retry_manual_commit(update_timestamp_operation)
            
        except Exception as e:
            logger.error("Failed to update last message timestamp", phone=phone, error=str(e))
            return False


# Global repository instance
user_repository = UserRepository()