"""
Gmail API integration module for the email processing app
Handles OAuth 2.0 authentication and Gmail API ops
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .config import GMAIL_SCOPES, CREDENTIALS_FILE, TOKEN_FILE

logger = logging.getLogger(__name__)


class GmailAPI:
    """
    API client for email operations
    Handles auth and provides methods to fetch and modify emails.
    """
    
    def __init__(self, credentials_file: str = CREDENTIALS_FILE, token_file: str = TOKEN_FILE):
        """
        Initialize Gmail API client
        Args:
            credentials_file: path to OAuth credentials file
            token_file: path to store/load the OAuth token
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        
    def authenticate(self) -> bool:
        """
        Authenticate with Gmail API using OAuth2
        Returns True if authentication successful else False
        """
        try:
            creds = None
            
            # Load existing token if available
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, GMAIL_SCOPES)
            
            # If no valid credentials available, let user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except Exception as e:
                        logger.error(f"Failed to refresh credentials: {e}")
                        creds = None
                
                if not creds:
                    if not os.path.exists(self.credentials_file):
                        logger.error(f"Credentials file not found: {self.credentials_file}")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, GMAIL_SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
            
            # Build the Gmail service
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Successfully authenticated with Gmail API")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def fetch_emails(self, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch recent emails from Gmail Inbox.
        Args:
            max_results: max no. of emails to fetch
        Returns list of email dictionaries with details
        """
        if not self.service:
            logger.error("Gmail service not initialized. Call authenticate() first")
            return []
        
        try:
            # Get list of email IDs
            results = self.service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            if not messages:
                logger.info("No messages found in inbox")
                return []
            
            logger.info(f"Found {len(messages)} messages in inbox")
            
            # Fetch detailed information for each email
            emails = []
            for message in messages:
                try:
                    email_detail = self._get_email_details(message['id'])
                    if email_detail:
                        emails.append(email_detail)
                except Exception as e:
                    logger.error(f"Failed to fetch details for message {message['id']}: {e}")
                    continue
            
            logger.info(f"Successfully fetched details for {len(emails)} emails")
            return emails
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []
    
    def _get_email_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific email.
        Args:
            message_id: Gmail message ID
        Returns email details dictionary (or None if fails)
        """
        try:
            message = self.service.users().messages().get(
                userId='me', 
                id=message_id,
                format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()
            
            headers = message.get('payload', {}).get('headers', [])
            header_dict = {header['name']: header['value'] for header in headers}
            
            # Extract email details
            email_data = {
                'id': message['id'],
                'thread_id': message.get('threadId', ''),
                'from_email': header_dict.get('From', ''),
                'subject': header_dict.get('Subject', ''),
                'received_date': self._parse_date(header_dict.get('Date', '')),
                'mailbox': 'INBOX',  # Default mailbox
                'is_read': 'UNREAD' not in message.get('labelIds', []),
                'snippet': message.get('snippet', ''),
                'label_ids': message.get('labelIds', [])
            }
            
            return email_data
            
        except HttpError as e:
            logger.error(f"Failed to get email details for {message_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing email {message_id}: {e}")
            return None
    
    def _parse_date(self, date_string: str) -> Optional[datetime]:
        """
        Parse email date string to datetime obj.
        Args:
            date_string: date string from email header
        Returns parsed datetime or None if parsing fails
        """
        if not date_string:
            return None
        
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_string)
        except Exception as e:
            logger.warning(f"Failed to parse date '{date_string}': {e}")
            return None
    
    def mark_as_read(self, message_id: str) -> bool:
        """
        Mark any email as READ by removing UNREAD label.
        Args:
            message_id: Gmail message ID
        Returns True if successful else False
        """
        return self._modify_labels(message_id, remove_label_ids=['UNREAD'])
    
    def mark_as_unread(self, message_id: str) -> bool:
        """
        Mark any email as unread by adding UNREAD label.
        Args:
            message_id: Gmail message ID
        Returns True if successful else False
        """
        return self._modify_labels(message_id, add_label_ids=['UNREAD'])
    
    def move_to_folder(self, message_id: str, folder_name: str) -> bool:
        """
        Move any email to a specified folder (label)
        Args:
            message_id: Gmail message ID
            folder_name: name of the folder/label to move to
        Returns True if successful else False
        """
        # First, create the label if it doesn't exist
        label_id = self._get_or_create_label(folder_name)
        if not label_id:
            return False
        
        return self._modify_labels(message_id, add_label_ids=[label_id])
    
    def _get_or_create_label(self, label_name: str) -> Optional[str]:
        """
        Get existing label ID or create new label.
        Args:
            label_name: name of the label
        Returns label ID or None if fails
        """
        try:
            # Try to find existing label
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            for label in labels:
                if label['name'] == label_name:
                    return label['id']
            
            # Create new label if not found
            label_object = {
                'name': label_name,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
            
            created_label = self.service.users().labels().create(
                userId='me', body=label_object).execute()
            
            logger.info(f"Created new label: {label_name}")
            return created_label['id']
            
        except HttpError as e:
            logger.error(f"Failed to get/create label '{label_name}': {e}")
            return None
        except Exception as e:
            logger.error(f"Error with label operation: {e}")
            return None
    
    def _modify_labels(self, message_id: str, add_label_ids: Optional[List[str]] = None, 
                      remove_label_ids: Optional[List[str]] = None) -> bool:
        """
        Modify labels for a message.
        Args:
            message_id: Gmail message ID
            add_label_ids: labels to add
            remove_label_ids: labels to remove
        Returns True if successful else False
        """
        try:
            body = {}
            if add_label_ids:
                body['addLabelIds'] = add_label_ids
            if remove_label_ids:
                body['removeLabelIds'] = remove_label_ids
            
            self.service.users().messages().modify(
                userId='me', id=message_id, body=body).execute()
            
            return True
            
        except HttpError as e:
            logger.error(f"Failed to modify labels for message {message_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error modifying labels: {e}")
            return False 