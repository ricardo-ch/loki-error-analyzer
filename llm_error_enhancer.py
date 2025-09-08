#!/usr/bin/env python3
"""
LLM Error Enhancer
Enriches Loki error analysis with local LLM insights and recommendations.
"""

import json
import requests
import argparse
import sys
import subprocess
import time
import signal
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml

class LLMErrorEnhancer:
    def __init__(self, llm_endpoint: str = "http://localhost:11434", model: str = "llama3.1:8b", auto_manage_ollama: bool = True):
        """Initialize the LLM enhancer with local LLM configuration."""
        self.llm_endpoint = llm_endpoint
        self.model = model
        self.enhanced_insights = {}
        self.auto_manage_ollama = auto_manage_ollama
        self.ollama_process = None
        self.ollama_started_by_script = False
    
    def check_ollama_installed(self) -> bool:
        """Check if Ollama is installed on the system."""
        try:
            result = subprocess.run(['ollama', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def check_ollama_running(self) -> bool:
        """Check if Ollama service is already running."""
        try:
            response = requests.get(f"{self.llm_endpoint}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def start_ollama(self) -> bool:
        """Start Ollama service if not already running."""
        if not self.auto_manage_ollama:
            return self.check_ollama_running()
        
        # Check if already running
        if self.check_ollama_running():
            print("✅ Ollama is already running")
            return True
        
        # Check if Ollama is installed
        if not self.check_ollama_installed():
            print("❌ Ollama is not installed. Please install it first:")
            print("   brew install ollama")
            return False
        
        print("🚀 Starting Ollama service...")
        try:
            # Start Ollama in the background
            self.ollama_process = subprocess.Popen(['ollama', 'serve'], 
                                                 stdout=subprocess.PIPE, 
                                                 stderr=subprocess.PIPE)
            self.ollama_started_by_script = True
            
            # Wait for Ollama to start
            print("⏳ Waiting for Ollama to start...")
            for i in range(30):  # Wait up to 30 seconds
                time.sleep(1)
                if self.check_ollama_running():
                    print("✅ Ollama started successfully")
                    return True
                print(f"   Waiting... ({i+1}/30)")
            
            print("❌ Ollama failed to start within 30 seconds")
            return False
            
        except Exception as e:
            print(f"❌ Failed to start Ollama: {e}")
            return False
    
    def stop_ollama(self):
        """Stop Ollama service if it was started by this script."""
        if self.auto_manage_ollama and self.ollama_started_by_script and self.ollama_process:
            print("🛑 Stopping Ollama service...")
            try:
                self.ollama_process.terminate()
                self.ollama_process.wait(timeout=10)
                print("✅ Ollama stopped successfully")
            except subprocess.TimeoutExpired:
                print("⚠️  Force killing Ollama process...")
                self.ollama_process.kill()
                self.ollama_process.wait()
            except Exception as e:
                print(f"⚠️  Error stopping Ollama: {e}")
            finally:
                self.ollama_process = None
                self.ollama_started_by_script = False
    
    def ensure_model_available(self) -> bool:
        """Ensure the required model is available, download if necessary."""
        try:
            # Check if model is available
            response = requests.get(f"{self.llm_endpoint}/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model['name'] for model in models]
                
                if any(self.model in name for name in model_names):
                    print(f"✅ Model {self.model} is available")
                    return True
            
            # Model not found, try to pull it
            print(f"📥 Model {self.model} not found. Downloading...")
            print("   This may take a few minutes...")
            
            result = subprocess.run(['ollama', 'pull', self.model], 
                                  capture_output=True, text=True, timeout=300)  # 5 min timeout
            
            if result.returncode == 0:
                print(f"✅ Model {self.model} downloaded successfully")
                return True
            else:
                print(f"❌ Failed to download model: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error checking/downloading model: {e}")
            return False
        
    def test_llm_connection(self) -> bool:
        """Test connection to local LLM service."""
        try:
            response = requests.post(f"{self.llm_endpoint}/api/generate", 
                json={
                    "model": self.model,
                    "prompt": "Hello, are you working?",
                    "stream": False
                }, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ LLM connection failed: {e}")
            return False
    
    def load_error_data(self, input_file: str) -> List[Dict]:
        """Load error data from JSON file."""
        try:
            with open(input_file, 'r') as f:
                if input_file.endswith('.jsonl'):
                    # Handle JSONL format
                    data = []
                    for line in f:
                        if line.strip():
                            data.append(json.loads(line))
                    return data
                else:
                    # Handle regular JSON format
                    return json.load(f)
        except Exception as e:
            print(f"❌ Error loading data from {input_file}: {e}")
            return []
    
    def extract_error_patterns(self, error_data: List[Dict]) -> Dict[str, Any]:
        """Extract key patterns from error data for LLM analysis."""
        patterns = {
            'total_errors': len(error_data),
            'services': {},
            'error_types': {},
            'time_distribution': {},
            'critical_errors': [],
            'top_error_messages': [],
            'namespace_breakdown': {}
        }
        
        for entry in error_data:
            # Service breakdown
            app = entry.get('labels', {}).get('app', 'unknown')
            if app not in patterns['services']:
                patterns['services'][app] = 0
            patterns['services'][app] += 1
            
            # Namespace breakdown
            namespace = entry.get('labels', {}).get('namespace', 'unknown')
            if namespace not in patterns['namespace_breakdown']:
                patterns['namespace_breakdown'][namespace] = 0
            patterns['namespace_breakdown'][namespace] += 1
            
            # Extract error message
            line_content = entry.get('line', '')
            try:
                parsed_line = json.loads(line_content)
                message = parsed_line.get('message', '')
                level = parsed_line.get('level', 'unknown')
                
                if level not in patterns['error_types']:
                    patterns['error_types'][level] = 0
                patterns['error_types'][level] += 1
                
                if message:
                    patterns['top_error_messages'].append({
                        'message': message[:200],  # Truncate for analysis
                        'app': app,
                        'level': level
                    })
                
                # Identify critical errors
                critical_keywords = ['timeout', 'connection refused', 'connection failed', 
                                   'eofexception', '503', '502', '500', 'fatal', 'critical']
                if any(keyword in message.lower() for keyword in critical_keywords):
                    patterns['critical_errors'].append({
                        'app': app,
                        'message': message[:100],
                        'level': level
                    })
                    
            except json.JSONDecodeError:
                continue
        
        # Sort and limit top messages
        patterns['top_error_messages'] = patterns['top_error_messages'][:10]
        patterns['critical_errors'] = patterns['critical_errors'][:5]
        
        return patterns
    
    def get_llm_analysis(self, error_patterns: Dict[str, Any]) -> Dict[str, str]:
        """Get LLM analysis of error patterns."""
        if not self.test_llm_connection():
            return {"error": "LLM service not available"}
        
        # Prepare context for LLM
        context = f"""
        Analyze these error logs from a production system and provide insights:
        
        Total Errors: {error_patterns['total_errors']}
        Services Affected: {list(error_patterns['services'].keys())}
        Error Types: {error_patterns['error_types']}
        Critical Errors: {len(error_patterns['critical_errors'])}
        
        Top Error Messages:
        {json.dumps(error_patterns['top_error_messages'][:5], indent=2)}
        
        Critical Errors:
        {json.dumps(error_patterns['critical_errors'], indent=2)}
        
        Please provide:
        1. Root Cause Analysis
        2. Impact Assessment
        3. Immediate Actions Required
        4. Long-term Recommendations
        5. Service Priority Ranking
        """
        
        try:
            response = requests.post(f"{self.llm_endpoint}/api/generate", 
                json={
                    "model": self.model,
                    "prompt": context,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower temperature for more focused analysis
                        "top_p": 0.9
                    }
                }, timeout=60)
            
            if response.status_code == 200:
                return {
                    "analysis": response.json()['response'],
                    "timestamp": datetime.now().isoformat(),
                    "model_used": self.model
                }
            else:
                return {"error": f"LLM API error: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"LLM analysis failed: {e}"}
    
    def generate_enhanced_report(self, original_analysis: Dict, llm_insights: Dict, 
                               output_file: str = None) -> str:
        """Generate enhanced report with LLM insights."""
        if not output_file:
            output_file = f"enhanced_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        report_content = f"""# Enhanced Loki Error Analysis Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Enhanced with:** {llm_insights.get('model_used', 'Unknown Model')}

## 🤖 AI-Powered Analysis

{llm_insights.get('analysis', 'No LLM analysis available')}

---

## 📊 Original Analysis Summary

- **Total Errors:** {original_analysis.get('total_errors', 'N/A')}
- **Services Affected:** {len(original_analysis.get('service_metrics', {}))}
- **Critical Errors:** {len(original_analysis.get('critical_errors', []))}

## 🔍 Service Health Overview

"""
        
        # Add service metrics if available
        if 'service_metrics' in original_analysis:
            for service, metrics in original_analysis['service_metrics'].items():
                report_content += f"### {service}\n"
                report_content += f"- **Total Errors:** {metrics.get('total_errors', 0)}\n"
                report_content += f"- **Critical Errors:** {metrics.get('critical_errors', 0)}\n"
                report_content += f"- **Affected Pods:** {metrics.get('unique_pods', 0)}\n\n"
        
        report_content += f"""
## 🚨 Critical Issues

"""
        
        # Add critical errors if available
        if 'critical_errors' in original_analysis:
            for i, error in enumerate(original_analysis['critical_errors'][:10], 1):
                report_content += f"{i}. **{error.get('app', 'Unknown')}** - {error.get('message', 'No message')[:80]}...\n"
                report_content += f"   - Pod: `{error.get('pod', 'Unknown')}`\n"
                report_content += f"   - Time: {error.get('timestamp', 'Unknown')}\n\n"
        
        report_content += f"""
## 📈 Recommendations

Based on the AI analysis above, focus on the recommended actions and long-term improvements.

---

*This report was enhanced using local LLM analysis. For technical questions, contact the DevOps team.*
"""
        
        # Write report
        with open(output_file, 'w') as f:
            f.write(report_content)
        
        return output_file
    
    def enhance_analysis(self, input_file: str, output_file: str = None) -> str:
        """Main method to enhance error analysis with LLM insights."""
        try:
            print("🔍 Loading error data...")
            error_data = self.load_error_data(input_file)
            
            if not error_data:
                print("❌ No error data found!")
                return None
            
            print(f"📊 Found {len(error_data)} error entries")
            
            # Start Ollama if needed
            if self.auto_manage_ollama:
                if not self.start_ollama():
                    print("❌ Failed to start Ollama. Proceeding without LLM analysis...")
                    return self.generate_fallback_report(error_data, output_file)
                
                # Ensure model is available
                if not self.ensure_model_available():
                    print("❌ Model not available. Proceeding without LLM analysis...")
                    return self.generate_fallback_report(error_data, output_file)
            
            print("🔍 Extracting error patterns...")
            error_patterns = self.extract_error_patterns(error_data)
            
            print("🤖 Getting LLM analysis...")
            llm_insights = self.get_llm_analysis(error_patterns)
            
            if 'error' in llm_insights:
                print(f"⚠️  LLM analysis failed: {llm_insights['error']}")
                print("📝 Generating report without LLM insights...")
                llm_insights = {"analysis": "LLM analysis unavailable"}
            
            print("📝 Generating enhanced report...")
            report_file = self.generate_enhanced_report(error_patterns, llm_insights, output_file)
            
            print(f"✅ Enhanced analysis complete! Report saved to: {report_file}")
            return report_file
            
        finally:
            # Always stop Ollama if we started it
            if self.auto_manage_ollama:
                self.stop_ollama()
    
    def generate_fallback_report(self, error_data: List[Dict], output_file: str = None) -> str:
        """Generate a basic report without LLM analysis."""
        if not output_file:
            output_file = f"basic_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        error_patterns = self.extract_error_patterns(error_data)
        
        report_content = f"""# Basic Error Analysis Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Note:** LLM analysis unavailable

## 📊 Error Summary

- **Total Errors:** {error_patterns['total_errors']}
- **Services Affected:** {len(error_patterns['services'])}
- **Critical Errors:** {len(error_patterns['critical_errors'])}

## 🔍 Service Breakdown

"""
        
        for service, count in error_patterns['services'].items():
            report_content += f"- **{service}:** {count} errors\n"
        
        report_content += f"""
## 🚨 Critical Errors

"""
        
        for error in error_patterns['critical_errors'][:10]:
            report_content += f"- **{error['app']}:** {error['message'][:100]}...\n"
        
        report_content += f"""
## 📝 Top Error Messages

"""
        
        for error in error_patterns['top_error_messages'][:5]:
            report_content += f"- {error['message'][:150]}...\n"
        
        report_content += f"""
---

*This is a basic analysis without AI enhancement. For full analysis, ensure Ollama is installed and running.*
"""
        
        with open(output_file, 'w') as f:
            f.write(report_content)
        
        return output_file

def signal_handler(signum, frame, enhancer):
    """Handle interrupt signals to ensure Ollama is stopped."""
    print("\n⏹️  Received interrupt signal. Cleaning up...")
    if enhancer:
        enhancer.stop_ollama()
    sys.exit(0)

def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description='LLM Error Enhancer - Add AI insights to Loki error analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 llm_error_enhancer.py prod_log.json
  python3 llm_error_enhancer.py prod_log.json --output enhanced_report.md
  python3 llm_error_enhancer.py prod_log.json --model llama3.1:8b --endpoint http://localhost:11434
  python3 llm_error_enhancer.py prod_log.json --no-auto-ollama  # Don't manage Ollama automatically
        """
    )
    
    parser.add_argument(
        'input_file',
        help='Input JSON/JSONL file with error data'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output markdown file name'
    )
    
    parser.add_argument(
        '--model', '-m',
        default='llama3.1:8b',
        help='LLM model to use (default: llama3.1:8b)'
    )
    
    parser.add_argument(
        '--endpoint', '-e',
        default='http://localhost:11434',
        help='LLM API endpoint (default: http://localhost:11434)'
    )
    
    parser.add_argument(
        '--no-auto-ollama',
        action='store_true',
        help='Disable automatic Ollama management (assume Ollama is already running)'
    )
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not Path(args.input_file).exists():
        print(f"❌ Input file not found: {args.input_file}")
        sys.exit(1)
    
    # Initialize enhancer
    enhancer = LLMErrorEnhancer(
        llm_endpoint=args.endpoint,
        model=args.model,
        auto_manage_ollama=not args.no_auto_ollama
    )
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, lambda s, f: signal_handler(s, f, enhancer))
    signal.signal(signal.SIGTERM, lambda s, f: signal_handler(s, f, enhancer))
    
    # Run enhancement
    try:
        if not args.no_auto_ollama:
            print("🤖 Auto-managing Ollama service...")
        else:
            print("🔌 Using existing Ollama service...")
            if not enhancer.test_llm_connection():
                print("⚠️  Warning: LLM service not available. Proceeding without AI analysis...")
        
        report_file = enhancer.enhance_analysis(args.input_file, args.output)
        if report_file:
            print(f"\n🎉 Enhancement complete!")
            print(f"📄 Report: {report_file}")
        else:
            print("❌ Enhancement failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Enhancement interrupted by user")
        enhancer.stop_ollama()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error during enhancement: {e}")
        enhancer.stop_ollama()
        sys.exit(1)

if __name__ == "__main__":
    main()
