"""
Database module for the email processing
handles PostgreSQL connection and email storage operations
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import os

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection

from .config import DATABASE_NAME

logger = logging.getLogger(__name__)


class EmailDatabase:
    """
    db client for email storage operations
    handles PostgreSQL connection and provides methods for storing and retrieving emails
    """
    
    def __init__(self, host: str = 'localhost', port: int = 5432, 
                 user: str = None, password: str = '', 
                 database: str = DATABASE_NAME):
        """
        initialize database connection parameters
        Args:
            host: Database host
            port: Database port
            user: Database username (defaults to current system user)
            password: Database password
            database: Database name
        """
        self.host = host
        self.port = port
        if user is None:
            self.user = os.getenv('USER')
            if self.user is None:
                self.user = 'postgres'
        else:
            self.user = user
        self.password = password
        self.database = database
        self.connection = None
    
    def connect(self) -> bool:
        """
        establish connection to postgres db
        Returns True if connection successful else False
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self.connection = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database
                )
                self.connection.autocommit = True
                self.is_connected = True
                logger.info(f"Successfully connected to database: {self.database}")
                return True
                
            except Exception as e:
                retry_count += 1
                logger.error(f"Database connection failed (attempt {retry_count}): {e}")
                if retry_count < max_retries:
                    import time
                    time.sleep(1)  #wait before retrying
                continue
        
        self.is_connected = False
        return False
    
    def create_tables(self) -> bool:
        """
        Create the emails table if it doesn't exist.
        Returns True if successful else False
        """
        if not self.connection:
            logger.error("Database not connected. Call connect() first.")
            return False

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS emails (
            id VARCHAR(255) PRIMARY KEY,
            thread_id VARCHAR(255),
            from_email TEXT,
            subject TEXT,
            received_date TIMESTAMP,
            mailbox TEXT,
            is_read BOOLEAN,
            snippet TEXT
        );
        """

        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(create_table_sql)
            logger.info("Emails table created/verified successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create emails table: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
    
    def store_emails(self, emails: List[Dict[str, Any]]) -> int:
        """
        Store emails in the database using INSERT ... ON CONFLICT DO NOTHING
        Args:
            emails: list of email dictionaries to store
        Returns no. of emails successfully stored
        """
        if not self.connection:
            logger.error("Database not connected. Call connect() first.")
            return 0

        if not emails:
            logger.info("No emails to store")
            return 0

        insert_sql = """
        INSERT INTO emails (id, thread_id, from_email, subject, received_date, mailbox, is_read, snippet)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING;
        """

        stored_count = 0
        cursor = None
        try:
            cursor = self.connection.cursor()
            for email in emails:
                try:
                    data = (
                        email.get('id', ''),
                        email.get('thread_id', ''),
                        email.get('from_email', ''),
                        email.get('subject', ''),
                        email.get('received_date'),
                        email.get('mailbox', 'INBOX'),
                        email.get('is_read', True),
                        email.get('snippet', '')
                    )
                    cursor.execute(insert_sql, data)
                    if cursor.rowcount > 0:
                        stored_count += 1
                except Exception as e:
                    logger.error(f"Error storing email {email.get('id', 'Unknown')}: {e}")
                    continue
            logger.info(f"Successfully stored {stored_count} new emails out of {len(emails)} total")
            return stored_count
        except Exception as e:
            logger.error(f"Database error during email storage: {e}")
            return stored_count
        finally:
            if cursor:
                cursor.close()
    
    def fetch_emails_for_processing(self) -> List[Dict[str, Any]]:
        """
        Fetch all emails from database for rule processing
        Returns list of email dictionaries
        """
        if not self.connection:
            logger.error("Database not connected. Call connect() first.")
            return []
        
        select_sql = """
        SELECT id, thread_id, from_email, subject, received_date, mailbox, is_read, snippet
        FROM emails
        ORDER BY received_date DESC;
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(select_sql)
            rows = cursor.fetchall()
            cursor.close()
            
            # convert to dictionaries
            column_names = ['id', 'thread_id', 'from_email', 'subject', 'received_date', 
                           'mailbox', 'is_read', 'snippet']
            
            email_list = []
            for row in rows:
                email_dict = dict(zip(column_names, row)) #zip to  combine multiple lists into pairs
                email_list.append(email_dict)
            
            logger.info(f"Fetched {len(email_list)} emails from database for processing")
            return email_list
            
        except Exception as e:
            logger.error(f"Failed to fetch emails from database: {e}")
            return []
    
    def update_email_status(self, email_id: str, is_read: Optional[bool] = None, mailbox: Optional[str] = None) -> bool:
        """
        update email read status and optionally mailbox in database
        Args:
            email_id: Email ID to update
            is_read: New read status (None to preserve current status)
            mailbox: New mailbox (optional)
        Returns True if successful else False
        """
        if not self.connection:
            logger.error("Database not connected. Call connect() first.")
            return False
        
        if mailbox and is_read is not None:
            update_sql = """
            UPDATE emails 
            SET is_read = %s, mailbox = %s 
            WHERE id = %s;
            """
            params = (is_read, mailbox, email_id)
        elif mailbox and is_read is None:
            update_sql = """
            UPDATE emails 
            SET mailbox = %s 
            WHERE id = %s;
            """
            params = (mailbox, email_id)
        elif mailbox is None and is_read is not None:
            update_sql = """
            UPDATE emails 
            SET is_read = %s 
            WHERE id = %s;
            """
            params = (is_read, email_id)
        else:
            logger.warning("No fields to update")
            return False
        
        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(update_sql, params)
            
            if cursor.rowcount > 0:
                logger.info(f"Updated email {email_id} status in database")
                return True
            else:
                logger.warning(f"Email {email_id} not found in database for update")
                return False
        except Exception as e:
            logger.error(f"Failed to update email {email_id} in database: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close() 