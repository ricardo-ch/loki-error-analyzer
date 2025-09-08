# Loki Error Analyzer

This folder contains all the files needed to run the Loki Error Analyzer independently.

## Files Included

- `run_analyzer.sh` - Main script to run the analyzer
- `loki_error_analyzer.py` - Python script that performs the analysis
- `config.yaml` - Configuration file for the analyzer
- `requirements.txt` - Python dependencies
- `README.md` - This documentation file

## Prerequisites

Before running the analyzer, ensure you have the following installed:

1. **Python 3** - Required for running the analyzer script
2. **kubectl** - Required for connecting to Kubernetes clusters
3. **logcli** - Grafana Loki command-line interface
   - Install from: https://grafana.com/docs/loki/latest/clients/logcli/
   - Configuration guide: [Loki LogCLI Configuration](https://www.notion.so/smgnet/Loki-4b4569ef1fa14918980fbffbbd479708)
4. **PyYAML** - Python YAML library
   - Install with: `pip3 install -r requirements.txt`

## Installation

1. Install Python dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```

2. Ensure kubectl is configured with access to the target Kubernetes cluster

3. Install logcli following the official documentation

## Usage

### Basic Usage

```bash
# Run analysis for development environment (default)
./run_analyzer.sh

# Run analysis for production environment
./run_analyzer.sh -e prod

# Run with debug mode enabled
./run_analyzer.sh -e prod -d

# Run without automatic cleanup
./run_analyzer.sh -e prod -c
```

### Command Line Options

- `-e, --env ENV` - Environment to analyze (dev, prod) [default: dev]
- `-d, --debug` - Enable debug mode
- `-c, --no-cleanup` - Disable automatic cleanup
- `-h, --help` - Show help message

### Examples

```bash
# Development environment analysis
./run_analyzer.sh

# Production environment analysis
./run_analyzer.sh -e prod

# Production analysis with debug mode
./run_analyzer.sh -e prod -d

# Production analysis without cleanup
./run_analyzer.sh -e prod -c
```

## Output Files

The analyzer generates the following files:

- `log.json` - Raw error logs from Loki
- `LOKI_ERROR_ANALYSIS_REPORT_DEV.md` - Analysis report for dev environment
- `LOKI_ERROR_ANALYSIS_REPORT_PROD.md` - Analysis report for prod environment

## Configuration

The `config.yaml` file contains all configuration options:

- **Loki Connection Settings**: Kubernetes context, namespace, service details
- **Query Parameters**: Time range, log level filters, output limits
- **Error Categories**: Customizable error classification patterns
- **Report Settings**: Organization details, report customization options

## Troubleshooting

### Common Issues

1. **Python 3 not found**: Ensure Python 3 is installed and in PATH
2. **kubectl not found**: Install kubectl and configure it for your cluster
3. **logcli not found**: Install logcli from the official documentation
4. **Permission denied**: Ensure the script has execute permissions: `chmod +x run_analyzer.sh`

### Debug Mode

Enable debug mode to get more detailed output:

```bash
./run_analyzer.sh -e prod -d
```

### Manual Cleanup

If the script doesn't clean up properly, manually stop kubectl port-forward processes:

```bash
pkill -f "kubectl port-forward"
```

## Environment-Specific Settings

### Development Environment
- Uses `dev-ricardo` organization ID
- Analyzes last 24 hours of logs
- Generates `LOKI_ERROR_ANALYSIS_REPORT_DEV.md`

### Production Environment
- Uses `prod-ricardo` organization ID
- Analyzes yesterday 19:00-22:00 time window
- Generates `LOKI_ERROR_ANALYSIS_REPORT_PROD.md`

## Support

For technical questions or issues, contact the DevOps team.
