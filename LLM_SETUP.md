# LLM Error Enhancer Setup Guide

This guide helps you set up local LLM integration to enhance your Loki error analysis.

## 🚀 Quick Start (Fully Automated)

### 1. Install Ollama
```bash
# Install Ollama
brew install ollama
```

### 2. Install Python Dependencies
```bash
pip3 install requests pyyaml
```

### 3. Run the Enhancer (No Manual Setup Required!)
```bash
# Basic usage - Ollama starts/stops automatically
python3 llm_error_enhancer.py prod_log.json

# With custom output file
python3 llm_error_enhancer.py prod_log.json --output enhanced_report.md

# With different model (will auto-download if needed)
python3 llm_error_enhancer.py prod_log.json --model mistral:7b
```

**🎉 That's it!** The script automatically:
- ✅ Starts Ollama if not running
- ✅ Downloads the model if not available
- ✅ Runs the analysis
- ✅ Stops Ollama when done

## 🤖 Automatic Features

### Auto-Ollama Management
The script now automatically manages Ollama for you:

- **Auto-Start**: Starts Ollama if not already running
- **Auto-Download**: Downloads the required model if not available
- **Auto-Stop**: Stops Ollama when analysis is complete
- **Graceful Shutdown**: Handles interruptions (Ctrl+C) properly

### Manual Control (Optional)
If you prefer to manage Ollama yourself:

```bash
# Disable auto-management
python3 llm_error_enhancer.py prod_log.json --no-auto-ollama
```

## 🔧 Alternative LLM Options

### Option 1: LM Studio (GUI)
1. Download from [lmstudio.ai](https://lmstudio.ai)
2. Install and start the app
3. Download a model (Llama 3.1 8B recommended)
4. Start the local server
5. Use endpoint: `http://localhost:1234/v1`

### Option 2: MLX (Apple Silicon Optimized)
```bash
# Install MLX
pip3 install mlx-lm

# Download a model
python3 -m mlx_lm.download --hf-repo mlx-community/Llama-3.1-8B-Instruct-4bit

# Run the model
python3 -m mlx_lm.generate --model mlx-community/Llama-3.1-8B-Instruct-4bit --prompt "Hello"
```

## 📊 Usage Examples

### Basic Enhancement
```bash
# Enhance your Loki analysis
python3 llm_error_enhancer.py prod_log.json
```

### Custom Configuration
```bash
# Use different model and endpoint
python3 llm_error_enhancer.py prod_log.json \
  --model mistral:7b \
  --endpoint http://localhost:1234/v1 \
  --output my_enhanced_report.md
```

### Integration with Main Analyzer
```bash
# 1. Run main analyzer
python3 loki_error_analyzer.py --env prod

# 2. Enhance the results
python3 llm_error_enhancer.py prod_log.json
```

## 🎯 What the Enhancer Adds

### AI-Powered Analysis
- **Root Cause Analysis**: Identifies likely causes of errors
- **Impact Assessment**: Evaluates business impact
- **Actionable Recommendations**: Specific steps to resolve issues
- **Service Priority Ranking**: Which services need immediate attention

### Enhanced Reporting
- **Executive Summaries**: Business-friendly language
- **Technical Deep Dives**: Detailed technical analysis
- **Trend Analysis**: Pattern recognition across errors
- **Prevention Strategies**: Long-term improvement suggestions

## 🔍 Supported Input Formats

- **JSON**: Regular JSON arrays
- **JSONL**: Newline-delimited JSON (Loki output format)
- **Error Logs**: Any structured error data

## 🛠️ Troubleshooting

### LLM Service Not Available
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if needed
ollama serve
```

### Model Not Found
```bash
# List available models
ollama list

# Pull a model
ollama pull llama3.1:8b
```

### Memory Issues
- Use smaller models: `llama3.1:7b` or `mistral:7b`
- Close other applications
- Consider using quantized models

## 📈 Performance Tips

### For MacBook M4
- **Recommended Model**: `llama3.1:8b` (good balance of quality/speed)
- **Memory Usage**: ~8GB RAM
- **Processing Time**: 30-60 seconds for typical analysis

### For Better Results
- Use models with 8B+ parameters for better analysis quality
- Ensure sufficient context window (8K+ tokens)
- Use temperature 0.3-0.7 for focused analysis

## 🔗 Integration with Existing Workflow

```bash
# Complete workflow
./run_analyzer.sh -e prod                    # Run main analysis
python3 llm_error_enhancer.py prod_log.json # Add AI insights
```

The enhancer works with any JSON/JSONL file containing error data, making it compatible with your existing Loki analyzer output.
