#!/usr/bin/env python3
"""
Database setup script for WikiBot.

This script creates all necessary database tables and indexes.
"""

import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlmodel import SQLModel
from src.data_access.database_client import database_client
from src.utils.logger import get_logger
from src.config.settings import settings
# Import all models to ensure they're registered with SQLModel metadata

logger = get_logger(__name__)


def create_tables():
    """Create all database tables using SQLModel metadata."""
    try:
        logger.info("Starting database table creation")
        
        # Use SQLModel.metadata.create_all() to create all tables
        # This automatically discovers all SQLModel classes with table=True
        SQLModel.metadata.create_all(database_client.engine)
        
        logger.info("Database tables created successfully using SQLModel metadata")
        
        # Verify tables were created
        with database_client.get_session() as session:
            # Check if we can query the tables
            result = session.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = [row[0] for row in result.fetchall()]
            
            logger.info("Created tables", tables=tables)
            
            # Expected tables from our SQLModel models
            expected_tables = [
                'users',
                'daily_facts', 
                'message_logs'
            ]
            
            created_model_tables = [table for table in expected_tables if table in tables]
            missing_tables = [table for table in expected_tables if table not in tables]
            
            if missing_tables:
                logger.warning("Some expected tables were not created", missing_tables=missing_tables)
            else:
                logger.info("All SQLModel tables created successfully", created_tables=created_model_tables)
        
        return True
        
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        return False


def verify_database_connection():
    """Verify database connection is working."""
    try:
        logger.info("Verifying database connection")
        
        if database_client.health_check():
            logger.info("Database connection verified successfully")
            return True
        else:
            logger.error("Database connection health check failed")
            return False
            
    except Exception as e:
        logger.error("Database connection verification failed", error=str(e))
        return False


def create_indexes():
    """Create additional indexes for better performance."""
    try:
        logger.info("Creating additional database indexes")
        
        with database_client.get_session() as session:
            # Create indexes that might not be automatically created
            indexes = [
                # User phone index (if not already unique)
                "CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);",
                
                # Daily facts date-language composite index (if not already unique)
                "CREATE INDEX IF NOT EXISTS idx_daily_facts_date_lang ON daily_facts(date, language);",
                
                # Message logs indexes
                "CREATE INDEX IF NOT EXISTS idx_message_logs_to ON message_logs(\"to\");",
                "CREATE INDEX IF NOT EXISTS idx_message_logs_created_at ON message_logs(created_at);",
                "CREATE INDEX IF NOT EXISTS idx_message_logs_status ON message_logs(status);",
                
                # User created_at index for analytics
                "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);",
                
                # Daily facts created_at index
                "CREATE INDEX IF NOT EXISTS idx_daily_facts_created_at ON daily_facts(created_at);"
            ]
            
            for index_sql in indexes:
                try:
                    session.execute(index_sql)
                    logger.debug("Index created", sql=index_sql)
                except Exception as e:
                    # Log but don't fail if index already exists
                    logger.warning("Index creation warning", sql=index_sql, error=str(e))
            
            session.commit()
        
        logger.info("Database indexes created successfully")
        return True
        
    except Exception as e:
        logger.error("Failed to create database indexes", error=str(e))
        return False


def setup_database():
    """Complete database setup."""
    logger.info("Starting database setup",
               database_url=settings.database.url.split('@')[1] if '@' in settings.database.url else settings.database.url)
    
    # Step 1: Verify connection
    if not verify_database_connection():
        logger.error("Database setup failed: Cannot connect to database")
        return False
    
    # Step 2: Create tables
    if not create_tables():
        logger.error("Database setup failed: Cannot create tables")
        return False
    
    # Step 3: Create additional indexes
    if not create_indexes():
        logger.warning("Database setup completed with warnings: Some indexes could not be created")
        # Don't fail the setup for index creation issues
    
    logger.info("Database setup completed successfully")
    return True


def main():
    """Main function to run database setup."""
    print("WikiBot Database Setup")
    print("=" * 30)
    print(f"Database URL: {settings.database.url.split('@')[1] if '@' in settings.database.url else settings.database.url}")
    print()
    
    try:
        success = setup_database()
        
        if success:
            print("✅ Database setup completed successfully!")
            print("\nNext steps:")
            print("1. Start the WikiBot application")
            print("2. Configure webhook endpoints")
            print("3. Test with /admin/health endpoint")
            sys.exit(0)
        else:
            print("❌ Database setup failed!")
            print("\nPlease check:")
            print("1. Database connection string is correct")
            print("2. Database server is running")
            print("3. Database exists and is accessible")
            print("4. User has necessary permissions")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n❌ Database setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Database setup failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()