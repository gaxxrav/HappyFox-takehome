"""
Main module for the email processing application
This module orchestrates the email processing flow: authentication, fetching,
storage, and rule-based processing
"""

import logging
import sys
import os
from typing import Optional

# handle imports for both direct execution and module import
try:
    from .config import get_validated_rules, EMAIL_FETCH_LIMIT, ERROR_LOG_FILE
    from .gmail_api import GmailAPI
    from .database import EmailDatabase
    from .rule_engine import RuleEngine
except ImportError:
    # add src directory to path for direct execution
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.config import get_validated_rules, EMAIL_FETCH_LIMIT, ERROR_LOG_FILE
    from src.gmail_api import GmailAPI
    from src.database import EmailDatabase
    from src.rule_engine import RuleEngine


def setup_logging() -> None:
    """
    Configure logging to write to both console log anf error log file
    """
    #format of logs are as below
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    #root logger config
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    #clear existing handlers
    root_logger.handlers.clear()
    
    #console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    #file handler for errors
    try:
        file_handler = logging.FileHandler(ERROR_LOG_FILE)
        file_handler.setLevel(logging.ERROR)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not create error log file: {e}")


def main() -> int:
    """
    Main function to manage mail processing workflow
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting Email Processing Application")
        
        # 1. load and validate rules
        logger.info("Loading email processing rules...")
        try:
            rules = get_validated_rules()
            if not rules:
                logger.warning("No valid rules found. Application will run but no processing will occur.")
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
            return 1
        
        # 2. initialize Gmail API
        logger.info("Initializing Gmail API...")
        gmail_api = GmailAPI()
        if not gmail_api.authenticate():
            logger.error("Gmail API authentication failed")
            return 1
        
        # 3. initialize database
        logger.info("Initializing database connection...")
        database = EmailDatabase()
        if not database.connect():
            logger.error("Database connection failed")
            return 1
        
        # create tables if they dont exist
        if not database.create_tables():
            logger.error("Failed to create database tables")
            return 1
        
        # 4. fetch emails from Gmail
        logger.info(f"Fetching up to {EMAIL_FETCH_LIMIT} emails from Gmail...")
        emails = gmail_api.fetch_emails(max_results=EMAIL_FETCH_LIMIT)
        if not emails:
            logger.warning("No emails fetched from Gmail")
            return 0
        
        # 5. store emails in database
        logger.info("Storing emails in database...")
        stored_count = database.store_emails(emails)
        logger.info(f"Stored {stored_count} new emails in database")
        
        # 6. process emails with rules
        if rules:
            logger.info("Processing emails with rules...")
            
            #fetch emails from database and process
            emails_for_processing = database.fetch_emails_for_processing()
            if not emails_for_processing:
                logger.warning("No emails found in database for processing")
                return 0
            
            #rule engine initializiation
            rule_engine = RuleEngine(gmail_api=gmail_api, database=database)
            
            #process emails
            action_counts = rule_engine.process_emails(emails_for_processing, rules)
            
            #logging results
            logger.info("Email processing completed:")
            logger.info(f"  - Total emails processed: {action_counts['total_processed']}")
            logger.info(f"  - Marked as read: {action_counts['mark_as_read']}")
            logger.info(f"  - Marked as unread: {action_counts['mark_as_unread']}")
            logger.info(f"  - Moved to folders: {action_counts['move']}")
        else:
            logger.info("No rules to process. Skipping rule processing.")
        
        # 7. cleanup
        database.close()
        logger.info("Email Processing Application completed successfully")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error in main application: {e}")
        return 1


def run_with_configuration(
    gmail_credentials_file: Optional[str] = None,
    rules_file: Optional[str] = None,
    database_host: str = 'localhost',
    database_port: int = 5432,
    database_user: str = 'postgres',
    database_password: str = '',
    database_name: str = 'email_processor',
    email_fetch_limit: int = EMAIL_FETCH_LIMIT
) -> int:
    """
    run the email processing application with custom configuration.
    Args:
        gmail_credentials_file: Path to Gmail API credentials file
        rules_file: Path to rules JSON file
        database_host: Database host
        database_port: Database port
        database_user: Database username
        database_password: Database password
        database_name: Database name
        email_fetch_limit: Maximum number of emails to fetch
        
    Returns exit code (0 for success, 1 for failure)
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting Email Processing Application with custom configuration")
        
        # 1. load and validate rules
        logger.info("Loading email processing rules...")
        try:
            rules = get_validated_rules(rules_file) if rules_file else get_validated_rules()
            if not rules:
                logger.warning("No valid rules found. Application will run but no processing will occur.")
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
            return 1
        
        # 2. initialize Gmail API
        logger.info("Initializing Gmail API...")
        gmail_api = GmailAPI(credentials_file=gmail_credentials_file)
        if not gmail_api.authenticate():
            logger.error("Gmail API authentication failed")
            return 1
        
        # 3. initialize database
        logger.info("Initializing database connection...")
        database = EmailDatabase(
            host=database_host,
            port=database_port,
            user=database_user,
            password=database_password,
            database=database_name
        )
        if not database.connect():
            logger.error("Database connection failed")
            return 1
        
        # create tables if they dont exist
        if not database.create_tables():
            logger.error("Failed to create database tables")
            return 1
        
        # 4. fetch emails from Gmail
        logger.info(f"Fetching up to {email_fetch_limit} emails from Gmail...")
        emails = gmail_api.fetch_emails(max_results=email_fetch_limit)
        if not emails:
            logger.warning("No emails fetched from Gmail")
            return 0
        
        # 5. store emails in database
        logger.info("Storing emails in database...")
        stored_count = database.store_emails(emails)
        logger.info(f"Stored {stored_count} new emails in database")
        
        # 6. process emails with rules
        if rules:
            logger.info("Processing emails with rules...")
            
            #fetch emails from database for processing
            emails_for_processing = database.fetch_emails_for_processing()
            if not emails_for_processing:
                logger.warning("No emails found in database for processing")
                return 0
            
            #rule engine initializiation
            rule_engine = RuleEngine(gmail_api=gmail_api, database=database)
            
            #process emails
            action_counts = rule_engine.process_emails(emails_for_processing, rules)
            
            #logging results
            logger.info("Email processing completed:")
            logger.info(f"  - Total emails processed: {action_counts['total_processed']}")
            logger.info(f"  - Marked as read: {action_counts['mark_as_read']}")
            logger.info(f"  - Marked as unread: {action_counts['mark_as_unread']}")
            logger.info(f"  - Moved to folders: {action_counts['move']}")
        else:
            logger.info("No rules to process. Skipping rule processing.")
        
        # 7. cleanup
        database.close()
        logger.info("Email Processing completed successfully")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error in main application: {e}")
        return 1


if __name__ == "__main__":
    # Setup logging
    setup_logging()
    
    # Run the application
    exit_code = main()
    sys.exit(exit_code) 