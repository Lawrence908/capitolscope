#!/usr/bin/env python3
"""
Logging configuration management script for CapitolScope.

This script provides utilities to manage logging levels at runtime
for debugging background tasks and other components.
"""

import sys
import os
from typing import Dict, Any

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.logging import (
    LogLevel, LogComponent, LOGGING_CONFIG, 
    update_log_level, enable_debug_logging, disable_debug_logging,
    get_component_log_level, is_debug_enabled
)


def print_current_config():
    """Print the current logging configuration."""
    print("=== Current Logging Configuration ===")
    print()
    
    for component in LogComponent:
        level = get_component_log_level(component)
        debug_enabled = is_debug_enabled(component)
        print(f"{component.value:20} | {level.value:8} | Debug: {debug_enabled}")
    
    print()
    print("Environment-specific overrides:")
    for env, config in LOGGING_CONFIG.items():
        if isinstance(config, dict) and any(isinstance(k, LogComponent) for k in config.keys()):
            print(f"  {env}:")
            for component, level in config.items():
                if isinstance(component, LogComponent):
                    print(f"    {component.value}: {level.value}")


def set_component_level(component_name: str, level_name: str):
    """Set the log level for a specific component."""
    try:
        component = LogComponent(component_name)
        level = LogLevel(level_name.upper())
        
        update_log_level(component, level)
        print(f"Updated {component.value} to {level.value}")
        
    except ValueError as e:
        print(f"Error: {e}")
        print(f"Valid components: {[c.value for c in LogComponent]}")
        print(f"Valid levels: {[l.value for l in LogLevel]}")


def enable_debug_for_component(component_name: str):
    """Enable debug logging for a specific component."""
    set_component_level(component_name, "DEBUG")


def disable_debug_for_component(component_name: str):
    """Disable debug logging for a specific component."""
    set_component_level(component_name, "INFO")


def enable_all_debug():
    """Enable debug logging for all components."""
    enable_debug_logging()
    print("Debug logging enabled for all components")


def disable_all_debug():
    """Disable debug logging for all components."""
    disable_debug_logging()
    print("Debug logging disabled for all components")


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python logging_config.py show                    # Show current config")
        print("  python logging_config.py set <component> <level> # Set component level")
        print("  python logging_config.py debug <component>       # Enable debug for component")
        print("  python logging_config.py info <component>        # Disable debug for component")
        print("  python logging_config.py debug-all               # Enable debug for all")
        print("  python logging_config.py info-all                # Disable debug for all")
        print()
        print("Components:", [c.value for c in LogComponent])
        print("Levels:", [l.value for l in LogLevel])
        return
    
    command = sys.argv[1].lower()
    
    if command == "show":
        print_current_config()
    
    elif command == "set" and len(sys.argv) == 4:
        component = sys.argv[2]
        level = sys.argv[3]
        set_component_level(component, level)
    
    elif command == "debug" and len(sys.argv) == 3:
        component = sys.argv[2]
        enable_debug_for_component(component)
    
    elif command == "info" and len(sys.argv) == 3:
        component = sys.argv[2]
        disable_debug_for_component(component)
    
    elif command == "debug-all":
        enable_all_debug()
    
    elif command == "info-all":
        disable_all_debug()
    
    else:
        print("Invalid command or arguments")
        print("Run without arguments to see usage")


if __name__ == "__main__":
    main() 