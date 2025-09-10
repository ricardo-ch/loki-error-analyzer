#!/bin/bash

# Loki Error Analyzer Runner Script
# This script runs the Loki error analyzer with proper environment setup

set -e

# Default values
ENVIRONMENT="dev"
DEBUG=false
CLEANUP=true
LIMIT=50000
TIMEOUT=600
LOG_LEVEL="error"
LOKI_QUERY=""
LOKI_QUERY_PARAMS=""

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -e, --env ENV        Environment to analyze (dev, prod) [default: dev]"
    echo "  -d, --debug          Enable debug mode"
    echo "  -c, --no-cleanup     Disable automatic cleanup"
    echo "  -l, --limit LIMIT    Maximum number of log entries [default: 50000]"
    echo "  -t, --timeout SEC    Query timeout in seconds [default: 600]"
    echo "  --log-level LEVEL    Log level filter (error, warn, info, debug, all) [default: error]"
    echo "  --loki-query QUERY   Custom Loki query (e.g., 'orgId=loki-tutti-prod')"
    echo "  --loki-query-params  JSON parameters for custom query"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                           # Run analysis for dev environment"
    echo "  $0 -e prod                   # Run analysis for prod environment"
    echo "  $0 -e prod -d                # Run analysis for prod with debug mode"
    echo "  $0 -e prod -l 10000          # Run with 10k limit"
    echo "  $0 -e prod -l 50000 -t 300   # Run with 50k limit and 5min timeout"
    echo "  $0 -e prod --log-level all   # Get all log levels (not just errors)"
    echo "  $0 -e dev --log-level warn   # Get warnings and errors only"
    echo "  $0 --loki-query 'orgId=loki-tutti-prod' --loki-query-params '{\"namespace\":\"live-tutti-services\",\"detected_level\":\"info\"}'"
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
        -l|--limit)
            LIMIT="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --loki-query)
            LOKI_QUERY="$2"
            shift 2
            ;;
        --loki-query-params)
            LOKI_QUERY_PARAMS="$2"
            shift 2
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

# Validate log level
if [[ "$LOG_LEVEL" != "error" && "$LOG_LEVEL" != "warn" && "$LOG_LEVEL" != "info" && "$LOG_LEVEL" != "debug" && "$LOG_LEVEL" != "all" ]]; then
    echo "Error: Log level must be one of: error, warn, info, debug, all"
    exit 1
fi

# Validate limit
if [[ "$LIMIT" -gt 100000 ]]; then
    echo "Warning: Limit $LIMIT is very large. This may cause timeouts."
    echo "Consider using a smaller limit (e.g., 50000) for better performance."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

# Validate timeout
if [[ "$TIMEOUT" -lt 60 ]]; then
    echo "Warning: Timeout $TIMEOUT seconds is very short. This may cause premature timeouts."
    echo "Consider using a longer timeout (e.g., 300) for better reliability."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

echo "=========================================="
echo "Loki Error Analyzer"
echo "=========================================="
echo "Environment: $ENVIRONMENT"
echo "Debug Mode: $DEBUG"
echo "Auto Cleanup: $CLEANUP"
echo "Limit: $LIMIT"
echo "Timeout: ${TIMEOUT}s"
echo "Log Level: $LOG_LEVEL"
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

# Set log level
echo "Setting log level to: $LOG_LEVEL"
python3 -c "
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Set log level based on command line argument
if '$LOG_LEVEL' == 'all':
    # For 'all', we need to modify the query to not filter by level
    # This will be handled in the Python script by modifying the query
    config['query']['level'] = 'all'
else:
    config['query']['level'] = '$LOG_LEVEL'

# Save updated config
with open('config.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False)

print('Log level set to: $LOG_LEVEL')
"

echo "Configuration updated successfully!"

# Run the analyzer
echo "Starting Loki Error Analyzer..."
echo ""

# Build command with parameters
CMD_ARGS=("--env" "$ENVIRONMENT" "--limit" "$LIMIT")

# Add custom Loki query arguments if provided
if [[ -n "$LOKI_QUERY" ]]; then
    CMD_ARGS+=("--loki-query" "$LOKI_QUERY")
fi

if [[ -n "$LOKI_QUERY_PARAMS" ]]; then
    CMD_ARGS+=("--loki-query-params" "$LOKI_QUERY_PARAMS")
fi

# Run the Python script with parameters
python3 loki_error_analyzer.py "${CMD_ARGS[@]}"

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
    if [[ "$ENVIRONMENT" == "prod" ]]; then
        REPORT_FILE="LOKI_ERROR_ANALYSIS_REPORT_PROD.md"
    else
        REPORT_FILE="LOKI_ERROR_ANALYSIS_REPORT_DEV.md"
    fi
    
    if [[ -f "$REPORT_FILE" ]]; then
        echo ""
        echo "Report preview:"
        echo "----------------------------------------"
        head -20 "$REPORT_FILE"
        echo "----------------------------------------"
        echo "Full report: $REPORT_FILE"
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
