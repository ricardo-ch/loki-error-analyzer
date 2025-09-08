# Loki Error Analyzer

This folder contains all the files needed to run the Loki Error Analyzer independently.

## Files Included

- `run_analyzer.sh` - Main script to run the analyzer
- `loki_error_analyzer.py` - Python script that performs the analysis
- `llm_error_enhancer.py` - AI-powered error analysis enhancer
- `config.yaml` - Configuration file for the analyzer
- `requirements.txt` - Python dependencies
- `LLM_SETUP.md` - LLM enhancer setup guide
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
5. **Ollama** (Optional) - For AI-powered analysis enhancement
   - Install with: `brew install ollama`
   - See `LLM_SETUP.md` for detailed setup

## Installation

1. Install Python dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```

2. Ensure kubectl is configured with access to the target Kubernetes cluster

3. Install logcli following the official documentation

4. (Optional) Install Ollama for AI-powered analysis:
   ```bash
   brew install ollama
   ```

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

### AI-Powered Analysis (Optional)

Enhance your error analysis with AI insights:

```bash
# Basic AI enhancement (Ollama starts/stops automatically)
python3 llm_error_enhancer.py prod_log.json

# With custom output file
python3 llm_error_enhancer.py prod_log.json --output enhanced_report.md

# With different AI model
python3 llm_error_enhancer.py prod_log.json --model mistral:7b

# Complete workflow: Loki analysis + AI enhancement
python3 loki_error_analyzer.py --env prod
python3 llm_error_enhancer.py prod_log.json
```

**AI Features:**
- 🤖 **Root Cause Analysis**: Identifies likely causes of errors
- 📊 **Detailed End-User Impact Analysis**: Comprehensive business impact assessment for top 3 error services
- 💰 **Financial Impact Assessment**: Revenue loss, cost implications, and business metrics
- 🎯 **Severity Classification**: Critical, High, Medium, Low impact levels
- ⚡ **Immediate Actions**: Emergency fixes and urgent remediation steps
- 📈 **Long-term Recommendations**: Strategic improvements and process enhancements
- 💬 **Communication Strategies**: User notification and stakeholder communication plans
- 🔍 **Service-Specific Intelligence**: Pre-built impact templates for key services

## Output Files

The analyzer generates the following files:

- `log.json` - Raw error logs from Loki
- `LOKI_ERROR_ANALYSIS_REPORT_DEV.md` - Analysis report for dev environment
- `LOKI_ERROR_ANALYSIS_REPORT_PROD.md` - Analysis report for prod environment
- `enhanced_analysis_YYYYMMDD_HHMMSS.md` - **AI-enhanced analysis with detailed end-user impact analysis**

### **Enhanced Analysis Report Features:**
- **🤖 AI-Powered Analysis**: LLM-generated insights and recommendations
- **🚨 Top 3 Services Impact Analysis**: Detailed business impact for highest error services
- **💰 Financial Impact Assessment**: Revenue loss, cost implications, business metrics
- **🎯 Severity Classification**: Critical, High, Medium, Low with business justification
- **⚡ Actionable Recommendations**: Immediate fixes and long-term strategic improvements
- **💬 Communication Strategies**: User notification and stakeholder communication plans
- **📊 Executive Summary**: CTO/executive-ready insights and decision support

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

## Complete Workflow

### Basic Analysis
```bash
# 1. Run Loki error analysis
python3 loki_error_analyzer.py --env prod

# 2. View the report
open prod_LOKI_ERROR_ANALYSIS_REPORT.md
```

### AI-Enhanced Analysis
```bash
# 1. Run Loki error analysis
python3 loki_error_analyzer.py --env prod

# 2. Enhance with AI insights (Ollama auto-starts/stops)
python3 llm_error_enhancer.py prod_log.json

# 3. View the enhanced report
open enhanced_analysis_*.md
```

## 🚨 Detailed End-User Impact Analysis

The enhanced LLM analyzer automatically generates comprehensive business impact analysis for the **top 3 error services** in every run. This provides executive-ready insights that go beyond technical error counts.

### **📊 What You Get:**

#### **For Each Top Service:**
- **Scale of Impact**: Error counts, rates, affected pods, percentage of system errors
- **Root Cause Analysis**: Technical root cause and error distribution patterns
- **Business Impact Assessment**: Direct and indirect user impact analysis
- **Severity Classification**: Critical, High, Medium, Low with business justification
- **Immediate Actions**: Emergency fixes, data investigation, financial reconciliation
- **Long-term Recommendations**: Strategic improvements and process enhancements
- **Communication Strategy**: User notification timelines and stakeholder communication

#### **Service-Specific Intelligence:**
- **`boost-fee-worker`**: Boost fee refund processing failures and financial impact
- **`frontend-mobile-api-v2`**: Mobile app functionality disruptions and user engagement
- **`imaginary-wrapper`**: Image processing failures and listing quality impact
- **Default templates**: For any other services with generic impact analysis

### **Example Analysis Output:**
```markdown
## 🚨 End User Impact Analysis: boost-fee-worker

### **📊 Scale of Impact**
- **Total Errors:** 7,317 (12.8% of all system errors)
- **Critical Errors:** 0 (0.0% of service errors)
- **Error Rate:** ~2.0 errors per hour
- **Affected Pods:** 4 pods

### **🔍 Root Cause Analysis**
**Primary Error:** Error handler threw an exception
**Error Distribution:** NullPointerException in boost fee refund processing

### **💰 Business Impact Assessment**
#### **Direct User Impact:**
1. **🔴 Boost Fee Refunds Not Processed**
   - Users who paid for listing boosts may not receive refunds
   - Affects seller experience and platform trust
   - **Financial impact**: Direct revenue loss from unprocessed refunds

### **🎯 Severity Classification**
**🔴 CRITICAL** - Business Critical - Immediate action required

### **⚡ Immediate Actions Required**
1. **🔧 Emergency Fix**
   - Add null checks for getConsentTime() in ListingServiceAdapter
   - Implement fallback logic for missing consent data
   - Deploy hotfix immediately
```

### **🎯 Business Value:**
- **Executive Ready**: Provides CTO/executive-level insights immediately
- **Actionable**: Specific steps for immediate and long-term remediation
- **Financial Focus**: Quantifies business impact and revenue implications
- **User-Centric**: Focuses on actual end-user experience and impact
- **Communication Ready**: Includes stakeholder communication strategies

### Using Shell Scripts
```bash
# Basic analysis
./run_analyzer.sh -e prod

# Then enhance with AI
python3 llm_error_enhancer.py prod_log.json
```

## Support

For technical questions or issues, contact the DevOps team.

### Additional Resources
- **LLM Setup Guide**: See `LLM_SETUP.md` for detailed AI enhancement setup
- **LogCLI Configuration**: [Loki LogCLI Configuration](https://www.notion.so/smgnet/Loki-4b4569ef1fa14918980fbffbbd479708)

## 🚀 Quick Reference

### **New in Enhanced Analysis:**
- **Automatic Top 3 Analysis**: Detailed end-user impact for highest error services
- **Business Impact Focus**: Financial, user experience, and operational impact assessment
- **Executive-Ready Reports**: CTO/executive-level insights and decision support
- **Service-Specific Intelligence**: Pre-built templates for key services
- **Communication Strategies**: User notification and stakeholder communication plans

### **One-Command Analysis:**
```bash
# Complete analysis with AI enhancement
python3 loki_error_analyzer.py --env prod && python3 llm_error_enhancer.py prod_log.json
```

### **Key Benefits:**
- **🎯 Actionable**: Specific immediate and long-term recommendations
- **💰 Business-Focused**: Financial impact and revenue implications
- **📊 Data-Driven**: Uses actual error metrics for severity classification
- **🔄 Automated**: No manual intervention required
- **💬 Communication-Ready**: Includes stakeholder communication strategies
