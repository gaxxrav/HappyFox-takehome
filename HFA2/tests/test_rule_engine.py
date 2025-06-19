"""
Unit tests for the rule engine module.

Tests rule matching logic and action functions with mocked dependencies.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Any

from src.rule_engine import RuleEngine


class TestRuleEngine:
    """Test cases for RuleEngine class."""
    
    @pytest.fixture
    def mock_gmail_api(self):
        """Create a mock Gmail API instance."""
        mock_api = Mock()
        mock_api.mark_as_read.return_value = True
        mock_api.mark_as_unread.return_value = True
        mock_api.move_to_folder.return_value = True
        return mock_api
    
    @pytest.fixture
    def mock_database(self):
        """Create a mock database instance."""
        mock_db = Mock()
        mock_db.update_email_status.return_value = True
        return mock_db
    
    @pytest.fixture
    def sample_email(self):
        """Create a sample email for testing."""
        return {
            'id': 'test_email_123',
            'thread_id': 'thread_456',
            'from_email': 'test@example.com',
            'subject': 'Test Subject',
            'received_date': '2024-01-15T10:30:00',
            'mailbox': 'INBOX',
            'is_read': False,
            'snippet': 'This is a test email snippet'
        }
    
    @pytest.fixture
    def sample_rules(self):
        """Create sample rules for testing."""
        return [
            {
                'rule_name': 'Test Rule 1',
                'predicate': 'ALL',
                'conditions': [
                    {'field': 'from', 'operator': 'contains', 'value': 'example.com'},
                    {'field': 'subject', 'operator': 'contains', 'value': 'Test'}
                ],
                'actions': [
                    {'action': 'mark_as_read'},
                    {'action': 'move', 'mailbox': 'TestFolder'}
                ]
            },
            {
                'rule_name': 'Test Rule 2',
                'predicate': 'ANY',
                'conditions': [
                    {'field': 'from', 'operator': 'contains', 'value': 'urgent.com'},
                    {'field': 'subject', 'operator': 'contains', 'value': 'Urgent'}
                ],
                'actions': [
                    {'action': 'mark_as_unread'}
                ]
            }
        ]
    
    def test_rule_engine_initialization(self, mock_gmail_api, mock_database):
        """Test RuleEngine initialization."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        assert rule_engine.gmail_api == mock_gmail_api
        assert rule_engine.database == mock_database
        assert 'contains' in rule_engine.operators
        assert 'less_than_days' in rule_engine.operators
    
    def test_operator_contains_true(self, mock_gmail_api, mock_database):
        """Test contains operator with matching values."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        result = rule_engine._operator_contains('test@example.com', 'example.com')
        assert result is True
    
    def test_operator_contains_false(self, mock_gmail_api, mock_database):
        """Test contains operator with non-matching values."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        result = rule_engine._operator_contains('test@example.com', 'other.com')
        assert result is False
    
    def test_operator_contains_case_insensitive(self, mock_gmail_api, mock_database):
        """Test contains operator is case insensitive."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        result = rule_engine._operator_contains('TEST@EXAMPLE.COM', 'example.com')
        assert result is True
    
    def test_operator_contains_empty_values(self, mock_gmail_api, mock_database):
        """Test contains operator with empty values."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        assert rule_engine._operator_contains('', 'test') is False
        assert rule_engine._operator_contains('test', '') is False
        assert rule_engine._operator_contains('', '') is False
    
    def test_operator_less_than_days_true(self, mock_gmail_api, mock_database):
        """Test less_than_days operator with recent date."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        # Create a date 1 day ago
        recent_date = (datetime.now() - timedelta(days=1)).isoformat()
        result = rule_engine._operator_less_than_days(recent_date, 2)
        assert result is True
    
    def test_operator_less_than_days_false(self, mock_gmail_api, mock_database):
        """Test less_than_days operator with old date."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        # Create a date 5 days ago
        old_date = (datetime.now() - timedelta(days=5)).isoformat()
        result = rule_engine._operator_less_than_days(old_date, 2)
        assert result is False
    
    def test_operator_less_than_days_invalid_date(self, mock_gmail_api, mock_database):
        """Test less_than_days operator with invalid date."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        result = rule_engine._operator_less_than_days('invalid_date', 2)
        assert result is False
    
    def test_operator_less_than_days_invalid_days(self, mock_gmail_api, mock_database):
        """Test less_than_days operator with invalid days value."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        recent_date = (datetime.now() - timedelta(days=1)).isoformat()
        result = rule_engine._operator_less_than_days(recent_date, 'invalid')
        assert result is False
    
    def test_get_email_field_value(self, mock_gmail_api, mock_database, sample_email):
        """Test getting email field values."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        assert rule_engine._get_email_field_value(sample_email, 'from') == 'test@example.com'
        assert rule_engine._get_email_field_value(sample_email, 'subject') == 'Test Subject'
        assert rule_engine._get_email_field_value(sample_email, 'received_date') == '2024-01-15T10:30:00'
        assert rule_engine._get_email_field_value(sample_email, 'unknown_field') is None
    
    def test_evaluate_condition_valid(self, mock_gmail_api, mock_database, sample_email):
        """Test evaluating a valid condition."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        condition = {'field': 'from', 'operator': 'contains', 'value': 'example.com'}
        result = rule_engine._evaluate_condition(sample_email, condition)
        assert result is True
    
    def test_evaluate_condition_invalid_field(self, mock_gmail_api, mock_database, sample_email):
        """Test evaluating condition with invalid field."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        condition = {'field': 'invalid_field', 'operator': 'contains', 'value': 'test'}
        result = rule_engine._evaluate_condition(sample_email, condition)
        assert result is False
    
    def test_evaluate_condition_missing_operator(self, mock_gmail_api, mock_database, sample_email):
        """Test evaluating condition with missing operator."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        condition = {'field': 'from', 'value': 'example.com'}
        result = rule_engine._evaluate_condition(sample_email, condition)
        assert result is False
    
    def test_evaluate_condition_unknown_operator(self, mock_gmail_api, mock_database, sample_email):
        """Test evaluating condition with unknown operator."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        condition = {'field': 'from', 'operator': 'unknown_op', 'value': 'example.com'}
        result = rule_engine._evaluate_condition(sample_email, condition)
        assert result is False
    
    def test_matches_rule_all_predicate_true(self, mock_gmail_api, mock_database, sample_email):
        """Test rule matching with ALL predicate and all conditions true."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        rule = {
            'rule_name': 'Test Rule',
            'predicate': 'ALL',
            'conditions': [
                {'field': 'from', 'operator': 'contains', 'value': 'example.com'},
                {'field': 'subject', 'operator': 'contains', 'value': 'Test'}
            ],
            'actions': []
        }
        
        result = rule_engine._matches_rule(sample_email, rule)
        assert result is True
    
    def test_matches_rule_all_predicate_false(self, mock_gmail_api, mock_database, sample_email):
        """Test rule matching with ALL predicate and one condition false."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        rule = {
            'rule_name': 'Test Rule',
            'predicate': 'ALL',
            'conditions': [
                {'field': 'from', 'operator': 'contains', 'value': 'example.com'},
                {'field': 'subject', 'operator': 'contains', 'value': 'NonExistent'}
            ],
            'actions': []
        }
        
        result = rule_engine._matches_rule(sample_email, rule)
        assert result is False
    
    def test_matches_rule_any_predicate_true(self, mock_gmail_api, mock_database, sample_email):
        """Test rule matching with ANY predicate and one condition true."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        rule = {
            'rule_name': 'Test Rule',
            'predicate': 'ANY',
            'conditions': [
                {'field': 'from', 'operator': 'contains', 'value': 'nonexistent.com'},
                {'field': 'subject', 'operator': 'contains', 'value': 'Test'}
            ],
            'actions': []
        }
        
        result = rule_engine._matches_rule(sample_email, rule)
        assert result is True
    
    def test_matches_rule_any_predicate_false(self, mock_gmail_api, mock_database, sample_email):
        """Test rule matching with ANY predicate and all conditions false."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        rule = {
            'rule_name': 'Test Rule',
            'predicate': 'ANY',
            'conditions': [
                {'field': 'from', 'operator': 'contains', 'value': 'nonexistent.com'},
                {'field': 'subject', 'operator': 'contains', 'value': 'NonExistent'}
            ],
            'actions': []
        }
        
        result = rule_engine._matches_rule(sample_email, rule)
        assert result is False
    
    def test_matches_rule_unknown_predicate(self, mock_gmail_api, mock_database, sample_email):
        """Test rule matching with unknown predicate."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        rule = {
            'rule_name': 'Test Rule',
            'predicate': 'UNKNOWN',
            'conditions': [
                {'field': 'from', 'operator': 'contains', 'value': 'example.com'}
            ],
            'actions': []
        }
        
        result = rule_engine._matches_rule(sample_email, rule)
        assert result is False
    
    def test_matches_rule_no_conditions(self, mock_gmail_api, mock_database, sample_email):
        """Test rule matching with no conditions."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        rule = {
            'rule_name': 'Test Rule',
            'predicate': 'ALL',
            'conditions': [],
            'actions': []
        }
        
        result = rule_engine._matches_rule(sample_email, rule)
        assert result is False
    
    def test_execute_mark_as_read_success(self, mock_gmail_api, mock_database):
        """Test successful mark as read execution."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        result = rule_engine._execute_mark_as_read('test_email_123')
        assert result is True
        
        mock_gmail_api.mark_as_read.assert_called_once_with('test_email_123')
        mock_database.update_email_status.assert_called_once_with('test_email_123', is_read=True)
    
    def test_execute_mark_as_unread_success(self, mock_gmail_api, mock_database):
        """Test successful mark as unread execution."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        result = rule_engine._execute_mark_as_unread('test_email_123')
        assert result is True
        
        mock_gmail_api.mark_as_unread.assert_called_once_with('test_email_123')
        mock_database.update_email_status.assert_called_once_with('test_email_123', is_read=False)
    
    def test_execute_move_to_folder_success(self, mock_gmail_api, mock_database, sample_email):
        """Test successful move to folder execution."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        result = rule_engine._execute_move_to_folder('test_email_123', 'TestFolder')
        assert result is True
        
        mock_gmail_api.move_to_folder.assert_called_once_with('test_email_123', 'TestFolder')
        mock_database.update_email_status.assert_called_once_with(
            'test_email_123', is_read=None, mailbox='TestFolder'
        )
    
    def test_execute_mark_as_read_gmail_failure(self, mock_gmail_api, mock_database):
        """Test mark as read execution with Gmail API failure."""
        mock_gmail_api.mark_as_read.return_value = False
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        result = rule_engine._execute_mark_as_read('test_email_123')
        assert result is False
    
    def test_execute_mark_as_read_database_failure(self, mock_gmail_api, mock_database):
        """Test mark as read execution with database failure."""
        mock_database.update_email_status.return_value = False
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        result = rule_engine._execute_mark_as_read('test_email_123')
        assert result is False
    
    def test_process_emails_empty_lists(self, mock_gmail_api, mock_database):
        """Test processing with empty email and rule lists."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        result = rule_engine.process_emails([], [])
        expected = {'mark_as_read': 0, 'mark_as_unread': 0, 'move': 0, 'total_processed': 0}
        assert result == expected
    
    def test_process_emails_no_rules(self, mock_gmail_api, mock_database, sample_email):
        """Test processing with emails but no rules."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        result = rule_engine.process_emails([sample_email], [])
        expected = {'mark_as_read': 0, 'mark_as_unread': 0, 'move': 0, 'total_processed': 0}
        assert result == expected
    
    def test_process_emails_successful_processing(self, mock_gmail_api, mock_database, sample_email, sample_rules):
        """Test successful email processing with rules."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        result = rule_engine.process_emails([sample_email], sample_rules)
        
        # Should have processed one email with mark_as_read and move actions
        assert result['total_processed'] == 1
        assert result['mark_as_read'] == 1
        assert result['move'] == 1
        assert result['mark_as_unread'] == 0
    
    def test_process_emails_with_exception_handling(self, mock_gmail_api, mock_database, sample_email):
        """Test processing with exception handling."""
        rule_engine = RuleEngine(gmail_api=mock_gmail_api, database=mock_database)
        
        # Mock a rule that will cause an exception
        problematic_rule = {
            'rule_name': 'Problematic Rule',
            'predicate': 'ALL',
            'conditions': [
                {'field': 'from', 'operator': 'contains', 'value': 'example.com'}
            ],
            'actions': [
                {'action': 'mark_as_read'}
            ]
        }
        
        # Mock the _evaluate_condition to raise an exception
        def mock_evaluate_condition(email, condition):
            raise Exception("Test exception")
        
        rule_engine._evaluate_condition = mock_evaluate_condition
        
        result = rule_engine.process_emails([sample_email], [problematic_rule])
        
        # Should handle exception gracefully and not process the email
        assert result['total_processed'] == 0
        assert result['mark_as_read'] == 0
