"""
rule engine module for the email processing app
handles parsing and evaluation of email processing rules
"""

import logging
from typing import Dict, List, Any, Callable
from datetime import datetime, timedelta
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


class RuleEngine:
    """
    rule engine for processing emails based on defined rules
    handles rule parsing, condition evaluation, and action execution
    """
    
    def __init__(self, gmail_api=None, database=None):
        """
        initialize rule engine
        
        Args:
            gmail_api: GmailAPI instance for executing actions in gmail
            database: EmailDatabase instance for updating email status
        """
        self.gmail_api = gmail_api
        self.database = database
        self.operators = {
            'contains': self._operator_contains,
            'less_than_days': self._operator_less_than_days
        }
    
    def process_emails(self, emails: List[Dict[str, Any]], rules: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        process emails against rules and execute actions
        
        Args:
            emails: List of email dictionaries to process
            rules: List of rule dictionaries to apply
            
        Returns dictionary with action execution counts
        """
        action_counts = {
            'mark_as_read': 0,
            'mark_as_unread': 0,
            'move': 0,
            'total_processed': 0
        }
        
        if not emails:
            logger.info("No emails to process")
            return action_counts
        
        if not rules:
            logger.info("No rules to apply")
            return action_counts
        
        logger.info(f"Processing {len(emails)} emails against {len(rules)} rules")
        
        for email in emails:
            try:
                email_actions = self._evaluate_email_rules(email, rules)
                if email_actions:
                    self._execute_actions(email, email_actions, action_counts)
                    action_counts['total_processed'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing email {email.get('id', 'Unknown')}: {e}")
                continue
        
        logger.info(f"Processing complete. Actions executed: {action_counts}")
        return action_counts
    
    def _evaluate_email_rules(self, email: Dict[str, Any], rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        evaluate all rules against a single email
        
        Args:
            email: Email dictionary to evaluate
            rules: List of rule dictionaries
            
        Returns list of actions to execute for this email
        """
        actions_to_execute = []
        
        for rule in rules:
            try:
                if self._matches_rule(email, rule):
                    logger.debug(f"Email {email.get('id', 'Unknown')} matches rule: {rule.get('rule_name', 'Unknown')}")
                    actions_to_execute.extend(rule.get('actions', []))
                    
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.get('rule_name', 'Unknown')}: {e}")
                continue
        
        return actions_to_execute
    
    def _matches_rule(self, email: Dict[str, Any], rule: Dict[str, Any]) -> bool:
        """
        check if an email matches a rule based on its conditions and predicate
        
        Args:
            email: Email dictionary to check
            rule: Rule dictionary with conditions and predicate
            
        Returns True if email matches rule else False
        """
        conditions = rule.get('conditions', [])
        predicate = rule.get('predicate', 'ALL')
        
        if not conditions:
            return False
        
        condition_results = []
        for condition in conditions:
            try:
                result = self._evaluate_condition(email, condition)
                condition_results.append(result)
            except Exception as e:
                logger.error(f"Error evaluating condition {condition}: {e}")
                condition_results.append(False)
        
        if predicate == 'ALL':
            return all(condition_results)
        elif predicate == 'ANY':
            return any(condition_results)
        else:
            logger.warning(f"Unknown predicate: {predicate}")
            return False
    
    def _evaluate_condition(self, email: Dict[str, Any], condition: Dict[str, Any]) -> bool:
        """
        evaluate a single condition against an email
        
        Args:
            email: Email dictionary to check
            condition: Condition dictionary with field, operator, and value
            
        Returns True if condition matches else False
        """
        field = condition.get('field', '')
        operator = condition.get('operator', '')
        value = condition.get('value', '')
        
        if not field or not operator:
            logger.warning(f"Invalid condition: missing field or operator")
            return False
        
        # Get email field value
        email_value = self._get_email_field_value(email, field)
        if email_value is None:
            return False
        
        # Apply operator
        if operator in self.operators:
            return self.operators[operator](email_value, value)
        else:
            logger.warning(f"Unknown operator: {operator}")
            return False
    
    def _get_email_field_value(self, email: Dict[str, Any], field: str) -> Any:
        """
        get the value of a field from an email
        
        Args:
            email: Email dictionary
            field: Field name to extract
            
        Returns field value if found else None
        """
        field_mapping = {
            'from': 'from_email',
            'subject': 'subject',
            'received_date': 'received_date'
        }
        
        email_field = field_mapping.get(field, field)
        return email.get(email_field)
    
    def _operator_contains(self, email_value: str, condition_value: str) -> bool:
        """
        check if email value contains the condition value (case-insensitive)
        
        Args:
            email_value: Value from email
            condition_value: Value to search for
            
        Returns True if email_value contains condition_value
        """
        if not email_value or not condition_value:
            return False
        
        return condition_value.lower() in email_value.lower()
    
    def _operator_less_than_days(self, email_value: str, condition_value: Any) -> bool:
        """
        check if email date is less than specified days ago
        
        Args:
            email_value: Date string from email
            condition_value: Number of days as string or int
            
        Returns True if email is newer than specified days
        """
        if not email_value:
            return False
        
        try:
            # Parse condition value to int
            days = int(condition_value)
            
            # Parse email date
            if isinstance(email_value, str):
                email_date = date_parser.parse(email_value)
            else:
                email_date = email_value
            
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=days)
            
            return email_date > cutoff_date
            
        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing date condition: {e}")
            return False
        except Exception as e:
            logger.error(f"Error in less_than_days operator: {e}")
            return False
    
    def _execute_actions(self, email: Dict[str, Any], actions: List[Dict[str, Any]], 
                        action_counts: Dict[str, int]):
        """
        execute actions for an email
        
        Args:
            email: Email dictionary
            actions: List of action dictionaries to execute
            action_counts: Dictionary to track action execution counts
        """
        email_id = email.get('id', '')
        
        for action in actions:
            try:
                action_type = action.get('action', '')
                
                if action_type == 'mark_as_read':
                    if self._execute_mark_as_read(email_id):
                        action_counts['mark_as_read'] += 1
                        
                elif action_type == 'mark_as_unread':
                    if self._execute_mark_as_unread(email_id):
                        action_counts['mark_as_unread'] += 1
                        
                elif action_type == 'move':
                    mailbox = action.get('mailbox', '')
                    if mailbox and self._execute_move_to_folder(email_id, mailbox):
                        action_counts['move'] += 1
                        
                else:
                    logger.warning(f"Unknown action type: {action_type}")
                    
            except Exception as e:
                logger.error(f"Error executing action {action} for email {email_id}: {e}")
                continue
    
    def _execute_mark_as_read(self, email_id: str) -> bool:
        """
        execute mark as read action
        
        Args:
            email_id: Email ID to mark as read
            
        Returns True if successful else False
        """
        success = True
        
        # Update Gmail API
        if self.gmail_api:
            if not self.gmail_api.mark_as_read(email_id):
                logger.error(f"Failed to mark email {email_id} as read in Gmail")
                success = False
        
        # Update database
        if self.database:
            if not self.database.update_email_status(email_id, is_read=True):
                logger.error(f"Failed to update email {email_id} read status in database")
                success = False
        
        if success:
            logger.info(f"Marked email {email_id} as read")
        
        return success
    
    def _execute_mark_as_unread(self, email_id: str) -> bool:
        """
        execute mark as unread action
        
        Args:
            email_id: Email ID to mark as unread
            
        Returns True if successful else False
        """
        success = True
        
        # Update Gmail API
        if self.gmail_api:
            if not self.gmail_api.mark_as_unread(email_id):
                logger.error(f"Failed to mark email {email_id} as unread in Gmail")
                success = False
        
        # Update database
        if self.database:
            if not self.database.update_email_status(email_id, is_read=False):
                logger.error(f"Failed to update email {email_id} read status in database")
                success = False
        
        if success:
            logger.info(f"Marked email {email_id} as unread")
        
        return success
    
    def _execute_move_to_folder(self, email_id: str, mailbox: str) -> bool:
        """
        execute move to folder action
        
        Args:
            email_id: Email ID to move
            mailbox: Target mailbox/folder name
            
        Returns True if successful else False
        """
        success = True
        
        # Update Gmail API
        if self.gmail_api:
            if not self.gmail_api.move_to_folder(email_id, mailbox):
                logger.error(f"Failed to move email {email_id} to folder {mailbox} in Gmail")
                success = False
        
        # Update database - only update mailbox, preserve current read status
        if self.database:
            if not self.database.update_email_status(email_id, is_read=None, mailbox=mailbox):
                logger.error(f"Failed to update email {email_id} mailbox in database")
                success = False
        
        if success:
            logger.info(f"Moved email {email_id} to folder {mailbox}")
        
        return success 