"""
Config Helper for EXE and Development Environment
================================================

Helper functions to handle config file paths in both development and EXE environments.
"""

import os
import sys
import json


def get_config_path(filename):
    """
    Get config file path that works in both development and EXE environments.
    
    Args:
        filename (str): Config filename (e.g., 'adaptive_params.json')
    
    Returns:
        str: Full path to config file
    """
    # Prefer user override first if exists
    user_override = os.path.join(os.path.expanduser('~'), 'Documents', 'ArbiTrader_Config', filename)
    if os.path.exists(user_override):
        return user_override
    
    if getattr(sys, 'frozen', False):
        # Running as EXE - use bundled resource path
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        candidate = os.path.join(base_path, 'config', filename)
        if os.path.exists(candidate):
            return candidate
    
    # Fallback to project relative path
    return os.path.join('config', filename)


def get_user_config_path(filename):
    """
    Get user config file path for saving settings in EXE environment.
    
    Args:
        filename (str): Config filename (e.g., 'adaptive_params.json')
    
    Returns:
        str: Full path to user config file
    """
    if getattr(sys, 'frozen', False):
        # Running as EXE - save to user's Documents folder
        user_docs = os.path.join(os.path.expanduser('~'), 'Documents')
        config_dir = os.path.join(user_docs, 'ArbiTrader_Config')
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, filename)
    else:
        # Running as script - use relative path
        return os.path.join('config', filename)


def load_config(filename):
    """
    Load config file that works in both environments.
    
    Args:
        filename (str): Config filename
    
    Returns:
        dict: Config data or empty dict if error
    """
    try:
        config_path = get_config_path(filename)
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config {filename}: {e}")
        return {}


def save_config(filename, data):
    """
    Save config file that works in both environments.
    
    Args:
        filename (str): Config filename
        data (dict): Config data to save
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        config_path = get_user_config_path(filename)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving config {filename}: {e}")
        return False
