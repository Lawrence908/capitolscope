#!/usr/bin/env python3
"""
Example usage of the enhanced congressional data fetch script with logging.

This demonstrates different logging configurations for various use cases.
"""

import sys
import logging
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent / 'src' / 'ingestion'))

from fetch_congress_data import main, configure_rate_limiting, setup_logging

def example_info_logging():
    """Example: Standard INFO level logging for normal operations"""
    print("=== Example 1: Standard INFO Logging ===")
    
    # Configure logging for normal operations
    logger = setup_logging(level=logging.INFO)
    
    # Configure conservative rate limiting
    configure_rate_limiting(request_delay=3.0, max_concurrent=2, max_retries=5)
    
    print("This would show:")
    print("- Processing progress")
    print("- Download summaries") 
    print("- Record counts")
    print("- Warnings and errors")
    print()

def example_debug_logging():
    """Example: DEBUG level logging for troubleshooting"""
    print("=== Example 2: DEBUG Logging for Troubleshooting ===")
    
    # Configure debug logging with file output
    logger = setup_logging(
        level=logging.DEBUG,
        log_file="congress_data_debug.log"
    )
    
    print("This would show:")
    print("- All INFO level messages PLUS:")
    print("- Individual member processing")
    print("- DocID validation details")
    print("- Existing PDF detection")
    print("- Individual record parsing")
    print("- Rate limiting delays")
    print("- All debug information saved to congress_data_debug.log")
    print()

def example_quiet_logging():
    """Example: Quiet mode for automated/production environments"""
    print("=== Example 3: Quiet Mode for Production ===")
    
    # Configure quiet logging (warnings and errors only)
    logger = setup_logging(level=logging.WARNING)
    
    print("This would show:")
    print("- Only warnings and errors")
    print("- Rate limiting issues")
    print("- Download failures")
    print("- Parsing errors")
    print("- Minimal output for scripts/automation")
    print()

def example_service_integration():
    """Example: How to integrate with a larger service architecture"""
    print("=== Example 4: Service Integration ===")
    
    print("For service integration, you can:")
    print("1. Import setup_logging from fetch_congress_data")
    print("2. Configure logging once at service startup")
    print("3. All congressional data components use the same logger")
    print()
    
    print("Example service code:")
    print("""
import logging
from your_service import setup_service_logging
from fetch_congress_data import setup_logging, CongressTrades

# Configure logging for your entire service
service_logger = setup_service_logging()

# Configure congressional data logging to match
congress_logger = setup_logging(
    level=logging.INFO,
    log_file="/var/log/your_service/congress_data.log"
)

# Now all congressional data operations use consistent logging
trades = CongressTrades(year=2024)
""")
    print()

if __name__ == "__main__":
    print("Congressional Data Logging Examples")
    print("==================================")
    print()
    
    example_info_logging()
    example_debug_logging() 
    example_quiet_logging()
    example_service_integration()
    
    print("Command Line Examples:")
    print("======================")
    print()
    print("# Standard processing with INFO logging")
    print("python fetch_congress_data.py 2024")
    print()
    print("# Debug logging with file output")
    print("python fetch_congress_data.py 2024 --log-level DEBUG --log-file debug.log")
    print()
    print("# Quiet mode for automation")
    print("python fetch_congress_data.py 2024 --quiet")
    print()
    print("# Conservative rate limiting with detailed logging")
    print("python fetch_congress_data.py 2024 --delay 5.0 --concurrent 1 --log-level DEBUG")
    print()
    print("# Production mode with error logging only")
    print("python fetch_congress_data.py 2024 --quiet --log-file /var/log/congress_errors.log") 