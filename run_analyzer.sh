#!/bin/bash

# Loki Error Analyzer Runner Script
# This script runs the Loki error analyzer with proper environment setup

set -e

# Default values
ENVIRONMENT="dev"
DEBUG=false
CLEANUP=true

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -e, --env ENV        Environment to analyze (dev, prod) [default: dev]"
    echo "  -d, --debug          Enable debug mode"
    echo "  -c, --no-cleanup     Disable automatic cleanup"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                   # Run analysis for dev environment"
    echo "  $0 -e prod           # Run analysis for prod environment"
    echo "  $0 -e prod -d        # Run analysis for prod with debug mode"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -d|--debug)
            DEBUG=true
            shift
            ;;
        -c|--no-cleanup)
            CLEANUP=false
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prod" ]]; then
    echo "Error: Environment must be 'dev' or 'prod'"
    exit 1
fi

echo "=========================================="
echo "Loki Error Analyzer"
echo "=========================================="
echo "Environment: $ENVIRONMENT"
echo "Debug Mode: $DEBUG"
echo "Auto Cleanup: $CLEANUP"
echo "=========================================="

# Check prerequisites
echo "Checking prerequisites..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    exit 1
fi

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed or not in PATH"
    exit 1
fi

# Check if logcli is available
if ! command -v logcli &> /dev/null; then
    echo "Error: logcli is not installed or not in PATH"
    echo "Please install logcli: https://grafana.com/docs/loki/latest/clients/logcli/"
    exit 1
fi

# Check if config.yaml exists
if [[ ! -f "config.yaml" ]]; then
    echo "Error: config.yaml not found in current directory"
    exit 1
fi

# Check if loki_error_analyzer.py exists
if [[ ! -f "loki_error_analyzer.py" ]]; then
    echo "Error: loki_error_analyzer.py not found in current directory"
    exit 1
fi

echo "Prerequisites check passed!"

# Clean up any existing kubectl port-forward processes
echo "Cleaning up existing kubectl port-forward processes..."
pkill -f "kubectl port-forward" || true
sleep 2

# Set environment-specific configurations
if [[ "$ENVIRONMENT" == "prod" ]]; then
    echo "Configuring for production environment..."
    
    # Update config for production
    python3 -c "
import yaml
import sys
from datetime import datetime, timedelta

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Set production-specific settings
config['loki']['context'] = 'platform-chili'
config['query']['org_id'] = 'prod-ricardo'

# Set time range for production (yesterday 19:00-22:00)
yesterday = datetime.now() - timedelta(days=1)
start_time = yesterday.replace(hour=19, minute=0, second=0, microsecond=0)
end_time = yesterday.replace(hour=22, minute=0, second=0, microsecond=0)

config['query']['start_date'] = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
config['query']['end_date'] = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
config['query']['days_back'] = 1

# Update report file name
config['analysis']['report_file'] = 'LOKI_ERROR_ANALYSIS_REPORT_PROD.md'

# Save updated config
with open('config.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False)

print('Production configuration applied')
"
else
    echo "Configuring for development environment..."
    
    # Update config for development
    python3 -c "
import yaml
import sys
from datetime import datetime, timedelta

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Set development-specific settings
config['loki']['context'] = 'platform-chili'
config['query']['org_id'] = 'dev-ricardo'

# Set time range for development (last 24 hours)
config['query']['start_date'] = None
config['query']['end_date'] = None
config['query']['days_back'] = 1

# Update report file name
config['analysis']['report_file'] = 'LOKI_ERROR_ANALYSIS_REPORT_DEV.md'

# Save updated config
with open('config.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False)

print('Development configuration applied')
"
fi

# Set debug mode if requested
if [[ "$DEBUG" == "true" ]]; then
    echo "Enabling debug mode..."
    python3 -c "
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Enable debug mode
config['analysis']['debug'] = True

# Save updated config
with open('config.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False)

print('Debug mode enabled')
"
fi

# Set cleanup mode
if [[ "$CLEANUP" == "false" ]]; then
    echo "Disabling automatic cleanup..."
    python3 -c "
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Disable auto cleanup
config['cleanup']['auto_cleanup'] = False

# Save updated config
with open('config.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False)

print('Automatic cleanup disabled')
"
fi

echo "Configuration updated successfully!"

# Run the analyzer
echo "Starting Loki Error Analyzer..."
echo ""

# Run the Python script
python3 loki_error_analyzer.py

# Check exit status
if [[ $? -eq 0 ]]; then
    echo ""
    echo "=========================================="
    echo "Analysis completed successfully!"
    echo "=========================================="
    
    # Show generated files
    echo "Generated files:"
    ls -la *.md *.json 2>/dev/null || echo "No markdown or JSON files found"
    
    # Show report content if it exists
    if [[ -f "LOKI_ERROR_ANALYSIS_REPORT_${ENVIRONMENT^^}.md" ]]; then
        echo ""
        echo "Report preview:"
        echo "----------------------------------------"
        head -20 "LOKI_ERROR_ANALYSIS_REPORT_${ENVIRONMENT^^}.md"
        echo "----------------------------------------"
        echo "Full report: LOKI_ERROR_ANALYSIS_REPORT_${ENVIRONMENT^^}.md"
    fi
    
else
    echo ""
    echo "=========================================="
    echo "Analysis failed!"
    echo "=========================================="
    exit 1
fi

# Final cleanup
if [[ "$CLEANUP" == "true" ]]; then
    echo ""
    echo "Performing final cleanup..."
    pkill -f "kubectl port-forward" || true
    echo "Cleanup completed"
fi

echo ""
echo "Done!"
