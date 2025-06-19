# Config for the Email Processing Application.
# This module handles loading config constants and rules from json files.

import json
import logging
from pathlib import Path
from typing import Dict, List, Any

#config constants
EMAIL_FETCH_LIMIT = 100
DATABASE_NAME = "email_processor"
RULES_FILE = "rules.json"
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"
ERROR_LOG_FILE = "errors.log"

#api scopes
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

logger = logging.getLogger(__name__)


def load_rules(rules_file_path: str = RULES_FILE) -> List[Dict[str, Any]]:
    """
    Load email processing rules from json
    Args:
        rules_file_path: Path to the rules.json file

    Returns list of rule dictionaries
    Raises:
        1. FileNotFoundError if rules file doesn't exist
        2. json.JSONDecodeError if rules file contains invalid json
    """
    try:
        rules_path = Path(rules_file_path)
        if not rules_path.exists():
            logger.error(f"Rules file not found: {rules_file_path}")
            raise FileNotFoundError(f"Rules file not found: {rules_file_path}")
        
        with open(rules_path, 'r', encoding='utf-8') as file:
            rules = json.load(file)
            
        if not isinstance(rules, list):
            logger.error("Rules file must contain a list of rules")
            raise ValueError("Rules file must contain a list of rules")
            
        logger.info(f"Successfully loaded {len(rules)} rules from {rules_file_path}")
        return rules
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in rules file: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading rules: {e}")
        raise


def validate_rule(rule: Dict[str, Any]) -> bool:
    """
    validate a single rule structure
    Args:
        rule: Rule dictionary to validate
        
    Returns True if rule is valid else False
    """
    required_fields = ['rule_name', 'predicate', 'conditions', 'actions']
    
    # Check required fields
    for field in required_fields:
        if field not in rule:
            logger.warning(f"Rule missing required field: {field}")
            return False
    
    # Validate predicate
    if rule['predicate'] not in ['ALL', 'ANY']:
        logger.warning(f"Invalid predicate: {rule['predicate']}")
        return False
    
    # Validate conditions
    if not isinstance(rule['conditions'], list) or len(rule['conditions']) == 0:
        logger.warning("Rule must have at least one condition")
        return False
    
    # Validate actions
    if not isinstance(rule['actions'], list) or len(rule['actions']) == 0:
        logger.warning("Rule must have at least one action")
        return False
    
    return True


def get_validated_rules(rules_file_path: str = RULES_FILE) -> List[Dict[str, Any]]:
    """
    Load and validate rules from json file.
    Args:
        rules_file_path: Path to the rules JSON file

    Returns list of validated rule dictionaries
    """
    rules = load_rules(rules_file_path)
    validated_rules = []
    
    for rule in rules:
        if validate_rule(rule):
            validated_rules.append(rule)
        else:
            logger.warning(f"Skipping invalid rule: {rule.get('rule_name', 'Unknown')}")
    
    logger.info(f"Loaded {len(validated_rules)} valid rules out of {len(rules)} total")
    return validated_rules 