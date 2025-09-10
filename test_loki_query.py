#!/usr/bin/env python3
"""
Test script for the new Loki query functionality
"""

import subprocess
import sys
import json

def test_loki_query():
    """Test the new Loki query functionality"""
    
    print("Testing Loki query functionality...")
    print("=" * 50)
    
    # Test command with the specific query requested
    cmd = [
        'python3', 'loki_error_analyzer.py',
        '--loki-query', 'orgId=loki-tutti-prod',
        '--loki-query-params', '{"namespace":"live-tutti-services","detected_level":"info"}',
        '--env', 'dev',
        '--limit', '100'  # Small limit for testing
    ]
    
    print("Command to execute:")
    print(' '.join(cmd))
    print()
    
    # Show what the LogQL query will look like
    print("This will generate the following LogQL query:")
    print('{namespace="live-tutti-services"} | detected_level!="info"')
    print()
    
    print("Note: This will query for logs where:")
    print("- orgId = loki-tutti-prod")
    print("- namespace = live-tutti-services") 
    print("- detected_level != info (i.e., error, warn, debug, etc.)")
    print()
    
    # Ask user if they want to proceed
    response = input("Do you want to run this test? (y/N): ").strip().lower()
    
    if response == 'y':
        try:
            print("Running test...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            print("STDOUT:")
            print(result.stdout)
            
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
            
            print(f"Exit code: {result.returncode}")
            
        except subprocess.TimeoutExpired:
            print("Test timed out after 5 minutes")
        except Exception as e:
            print(f"Error running test: {e}")
    else:
        print("Test cancelled by user")

if __name__ == "__main__":
    test_loki_query()
