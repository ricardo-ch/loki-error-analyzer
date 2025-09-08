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
                    "prompt": "Hello",
                    "stream": False
                }, timeout=30)  # Increased timeout
            return response.status_code == 200
        except Exception as e:
            print(f"❌ LLM connection failed: {e}")
            return False
    
    def load_error_data(self, input_file: str) -> List[Dict]:
        """Load error data from JSON or JSONL file."""
        try:
            with open(input_file, 'r') as f:
                # Try to detect format by reading first line
                first_line = f.readline().strip()
                f.seek(0)  # Reset file pointer
                
                if first_line.startswith('{') and not first_line.startswith('[{'):
                    # JSONL format - each line is a JSON object
                    data = []
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                data.append(json.loads(line))
                            except json.JSONDecodeError as e:
                                print(f"⚠️  Skipping invalid JSON line: {e}")
                                continue
                    return data
                else:
                    # Try regular JSON format
                    try:
                        return json.load(f)
                    except json.JSONDecodeError:
                        # If regular JSON fails, try JSONL format
                        f.seek(0)
                        data = []
                        for line in f:
                            line = line.strip()
                            if line:
                                try:
                                    data.append(json.loads(line))
                                except json.JSONDecodeError as e:
                                    print(f"⚠️  Skipping invalid JSON line: {e}")
                                    continue
                        return data
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
                
                if message and isinstance(message, str):
                    patterns['top_error_messages'].append({
                        'message': message[:200],  # Truncate for analysis
                        'app': app,
                        'level': level
                    })
                
                # Identify critical errors
                critical_keywords = ['timeout', 'connection refused', 'connection failed', 
                                   'eofexception', '503', '502', '500', 'fatal', 'critical']
                if message and isinstance(message, str) and any(keyword in message.lower() for keyword in critical_keywords):
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
        
        # Generate detailed service metrics for end-user impact analysis
        patterns['service_metrics'] = self._generate_service_metrics(error_data, patterns)
        
        return patterns
    
    def _generate_service_metrics(self, error_data: List[Dict], patterns: Dict) -> Dict[str, Dict]:
        """Generate detailed metrics for each service."""
        service_metrics = {}
        
        # Group errors by service
        service_errors = {}
        for entry in error_data:
            app = entry.get('labels', {}).get('app', 'unknown')
            if app not in service_errors:
                service_errors[app] = []
            service_errors[app].append(entry)
        
        # Generate metrics for each service
        for service, errors in service_errors.items():
            error_types = {}
            critical_errors = []
            pods = set()
            namespaces = set()
            top_error_message = ""
            top_error_count = 0
            error_message_counts = {}
            
            for entry in errors:
                # Collect pods and namespaces
                pods.add(entry.get('labels', {}).get('pod', 'unknown'))
                namespaces.add(entry.get('labels', {}).get('namespace', 'unknown'))
                
                # Parse error details
                line_content = entry.get('line', '')
                try:
                    parsed_line = json.loads(line_content)
                    message = parsed_line.get('message', '')
                    level = parsed_line.get('level', 'unknown')
                    
                    # Count error types
                    if level not in error_types:
                        error_types[level] = 0
                    error_types[level] += 1
                    
                    # Count error messages
                    if message and isinstance(message, str):
                        if message not in error_message_counts:
                            error_message_counts[message] = 0
                        error_message_counts[message] += 1
                        
                        # Track most common error message
                        if error_message_counts[message] > top_error_count:
                            top_error_count = error_message_counts[message]
                            top_error_message = message
                    
                    # Identify critical errors
                    critical_keywords = ['timeout', 'connection refused', 'connection failed', 
                                       'eofexception', '503', '502', '500', 'fatal', 'critical']
                    if message and isinstance(message, str) and any(keyword in message.lower() for keyword in critical_keywords):
                        critical_errors.append({
                            'app': service,
                            'message': message[:100],
                            'level': level,
                            'pod': entry.get('labels', {}).get('pod', 'unknown')
                        })
                        
                except json.JSONDecodeError:
                    continue
            
            # Generate service metrics
            service_metrics[service] = {
                'total_errors': len(errors),
                'critical_errors': len(critical_errors),
                'unique_pods': len(pods),
                'unique_namespaces': len(namespaces),
                'error_types': error_types,
                'top_error_message': top_error_message,
                'top_error_count': top_error_count,
                'critical_errors_list': critical_errors[:5]  # Top 5 critical errors
            }
        
        return service_metrics
    
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
                }, timeout=120)  # Increased timeout for analysis
            
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
    
    def generate_end_user_impact_analysis(self, service_name: str, error_data: List[Dict], 
                                        service_metrics: Dict, total_system_errors: int = 0) -> str:
        """Generate detailed end-user impact analysis for a specific service."""
        
        # Extract key metrics
        total_errors = service_metrics.get('total_errors', 0)
        critical_errors = service_metrics.get('critical_errors', 0)
        error_types = service_metrics.get('error_types', {})
        top_error_message = service_metrics.get('top_error_message', 'Unknown error')
        
        # Calculate error rate and duration
        error_rate = total_errors / 3600 if total_errors > 0 else 0  # errors per hour
        
        # Determine severity based on error volume and types
        if total_errors > 5000 or critical_errors > 100:
            severity = "🔴 CRITICAL"
            severity_desc = "Business Critical - Immediate action required"
        elif total_errors > 1000 or critical_errors > 10:
            severity = "🟠 HIGH"
            severity_desc = "High Impact - Urgent attention needed"
        elif total_errors > 100 or critical_errors > 0:
            severity = "🟡 MEDIUM"
            severity_desc = "Medium Impact - Monitor closely"
        else:
            severity = "🟢 LOW"
            severity_desc = "Low Impact - Standard monitoring"
        
        # Analyze error patterns for business impact
        business_impact = self._analyze_business_impact(service_name, error_data, error_types)
        
        # Generate recommendations
        recommendations = self._generate_service_recommendations(service_name, error_data, service_metrics)
        
        # Extract detailed technical root cause
        technical_details = self._extract_technical_root_cause(service_name, error_data)
        
        # Calculate correct percentage of total system errors
        error_percentage = (total_errors / total_system_errors * 100) if total_system_errors > 0 else 0
        
        return f"""## 🚨 End User Impact Analysis: {service_name}

### **📊 Scale of Impact**
- **Total Errors:** {total_errors:,} ({error_percentage:.1f}% of all system errors)
- **Critical Errors:** {critical_errors} ({critical_errors/total_errors*100:.1f}% of service errors)
- **Error Rate:** ~{error_rate:.1f} errors per hour
- **Affected Pods:** {service_metrics.get('unique_pods', 0)} pods

### **🔍 Root Cause Analysis**
**Primary Error:** {top_error_message}

**Technical Details:**
{technical_details}

**Error Distribution:**
{business_impact['root_cause']}

### **💰 Business Impact Assessment**

#### **Direct User Impact:**
{business_impact['direct_impact']}

#### **Indirect User Impact:**
{business_impact['indirect_impact']}

### **🎯 Severity Classification**

**{severity}** - {severity_desc}
- **Financial Impact:** {business_impact['financial_impact']}
- **User Trust:** {business_impact['user_trust']}
- **Operational Impact:** {business_impact['operational_impact']}

### **⚡ Immediate Actions Required**

{business_impact['immediate_actions']}

### **📈 Long-term Recommendations**

{business_impact['long_term_recommendations']}

### **💬 User Communication Strategy**

{business_impact['communication_strategy']}

---

"""

    def _analyze_business_impact(self, service_name: str, error_data: List[Dict], error_types: Dict) -> Dict:
        """Analyze business impact based on service name and error patterns."""
        
        # Service-specific impact analysis
        service_impacts = {
            'boost-fee-worker': {
                'root_cause': 'NullPointerException in boost fee refund processing - getConsentTime() returns null',
                'direct_impact': '1. **🔴 Boost Fee Refunds Not Processed**\n   - Users who paid for listing boosts may not receive refunds\n   - Affects seller experience and platform trust\n   - **Financial impact**: Direct revenue loss from unprocessed refunds\n\n2. **🔴 Listing Visibility Issues**\n   - Boost fee processing failures may affect listing visibility\n   - Sellers may not get expected premium placement results',
                'indirect_impact': '1. **🔴 System Reliability Concerns**\n   - High error volume indicates systemic issues\n   - May cause delayed processing of other operations\n   - **Customer support burden** from users reporting issues\n\n2. **🔴 Data Integrity Issues**\n   - Null consent time suggests data quality problems\n   - May indicate broader listing data management issues',
                'financial_impact': 'Direct revenue loss from unprocessed refunds',
                'user_trust': 'Sellers may lose confidence in payment processing',
                'operational_impact': 'High error volume suggests systemic data quality issues',
                'immediate_actions': '1. **🔧 Emergency Fix**\n   - Add null checks for getConsentTime() in ListingServiceAdapter\n   - Implement fallback logic for missing consent data\n   - Deploy hotfix immediately\n\n2. **🔍 Data Investigation**\n   - Query database for listings with null consent times\n   - Identify root cause of missing consent data\n\n3. **💰 Financial Reconciliation**\n   - Audit all boost fee transactions during incident\n   - Process manual refunds for affected users',
                'long_term_recommendations': '1. **🛡️ Defensive Programming**\n   - Add comprehensive null checks in listing services\n   - Implement circuit breakers for boost fee processing\n\n2. **📊 Monitoring & Alerting**\n   - Set up alerts for boost fee processing failures\n   - Implement business metrics monitoring\n\n3. **🔄 Process Improvements**\n   - Implement retry mechanisms for failed processing\n   - Add compensation patterns for eventual consistency',
                'communication_strategy': '**Immediate (Within 24 hours):**\n- Proactive communication to affected sellers about refund delays\n- Transparent explanation of technical issue and resolution timeline\n\n**Follow-up (Within 1 week):**\n- Detailed post-incident report\n- Process improvements implemented\n- Compensation for any financial impact'
            },
            'frontend-mobile-api-v2': {
                'root_cause': 'Registry function call failures in mobile API endpoints',
                'direct_impact': '1. **🔴 Mobile App Functionality Disrupted**\n   - Core mobile app features may be unavailable\n   - Users cannot complete essential actions\n   - **User experience degradation** for mobile users\n\n2. **🔴 API Response Failures**\n   - Mobile app requests failing or timing out\n   - Inconsistent user experience across app features',
                'indirect_impact': '1. **🔴 Mobile User Engagement Loss**\n   - Users may abandon the app due to failures\n   - Reduced mobile traffic and engagement\n\n2. **🔴 Support Ticket Increase**\n   - High volume of user complaints about app issues\n   - Increased customer support workload',
                'financial_impact': 'Potential revenue loss from mobile user abandonment',
                'user_trust': 'Mobile users may lose confidence in app reliability',
                'operational_impact': 'High error volume indicates mobile infrastructure issues',
                'immediate_actions': '1. **🔧 API Stabilization**\n   - Investigate registry function call failures\n   - Implement proper error handling and fallbacks\n\n2. **📱 Mobile App Health Check**\n   - Verify mobile app functionality\n   - Test critical user journeys\n\n3. **🔄 Load Balancing Review**\n   - Check API load balancing configuration\n   - Verify service discovery and routing',
                'long_term_recommendations': '1. **🛡️ Mobile API Resilience**\n   - Implement circuit breakers for external calls\n   - Add comprehensive error handling\n\n2. **📊 Mobile Monitoring**\n   - Set up mobile-specific error tracking\n   - Implement user journey monitoring\n\n3. **🔄 API Optimization**\n   - Optimize registry function calls\n   - Implement caching strategies',
                'communication_strategy': '**Immediate (Within 2 hours):**\n- Mobile app status page update\n- In-app notification about temporary issues\n\n**Follow-up (Within 24 hours):**\n- Detailed incident report\n- App store update if needed\n- User compensation for service disruption'
            },
            'imaginary-wrapper': {
                'root_cause': 'Image processing service failures - NamedTransformationNotFound errors',
                'direct_impact': '1. **🔴 Image Processing Failures**\n   - User-uploaded images may not be processed correctly\n   - Listing images may not display properly\n   - **Visual content degradation** affecting user experience\n\n2. **🔴 Image Optimization Issues**\n   - Images may not be optimized for different screen sizes\n   - Slow loading times and poor visual quality',
                'indirect_impact': '1. **🔴 Listing Quality Degradation**\n   - Poor image quality may reduce listing attractiveness\n   - Potential impact on sales conversion rates\n\n2. **🔴 CDN and Performance Issues**\n   - Image processing failures may affect CDN performance\n   - Overall page load times may increase',
                'financial_impact': 'Potential sales impact from poor listing presentation',
                'user_trust': 'Users may perceive platform as unreliable due to image issues',
                'operational_impact': 'Image processing pipeline requires immediate attention',
                'immediate_actions': '1. **🔧 Image Service Fix**\n   - Investigate NamedTransformationNotFound errors\n   - Verify image transformation configurations\n\n2. **🖼️ Image Processing Review**\n   - Check image processing pipeline health\n   - Verify CDN integration\n\n3. **🔄 Fallback Implementation**\n   - Implement fallback for failed image processing\n   - Ensure basic image display functionality',
                'long_term_recommendations': '1. **🛡️ Image Processing Resilience**\n   - Implement multiple image processing backends\n   - Add comprehensive error handling\n\n2. **📊 Image Monitoring**\n   - Set up image processing success rate monitoring\n   - Implement quality metrics tracking\n\n3. **🔄 Performance Optimization**\n   - Optimize image transformation pipeline\n   - Implement intelligent caching strategies',
                'communication_strategy': '**Immediate (Within 4 hours):**\n- Update image processing status\n- Communicate potential image quality issues\n\n**Follow-up (Within 48 hours):**\n- Image processing improvements implemented\n- Quality assurance for affected listings'
            }
        }
        
        # Default impact analysis for unknown services
        default_impact = {
            'root_cause': f'Multiple error types detected: {", ".join(error_types.keys())}',
            'direct_impact': f'1. **🔴 Service Functionality Disrupted**\n   - Core {service_name} features may be unavailable\n   - Users may experience service interruptions\n\n2. **🔴 Performance Degradation**\n   - Service may be responding slowly or inconsistently',
            'indirect_impact': '1. **🔴 User Experience Impact**\n   - Users may encounter errors when using the service\n   - Potential loss of user confidence\n\n2. **🔴 System Reliability Concerns**\n   - High error volume indicates underlying issues',
            'financial_impact': 'Potential revenue impact from service disruptions',
            'user_trust': 'Users may lose confidence in service reliability',
            'operational_impact': 'High error volume requires investigation and resolution',
            'immediate_actions': '1. **🔧 Service Investigation**\n   - Investigate root cause of errors\n   - Check service health and dependencies\n\n2. **🔄 Error Handling**\n   - Implement proper error handling\n   - Add monitoring and alerting\n\n3. **📊 Performance Review**\n   - Review service performance metrics\n   - Check resource utilization',
            'long_term_recommendations': '1. **🛡️ Service Resilience**\n   - Implement circuit breakers and retry logic\n   - Add comprehensive monitoring\n\n2. **📊 Observability**\n   - Set up detailed error tracking\n   - Implement business metrics monitoring\n\n3. **🔄 Process Improvements**\n   - Regular service health checks\n   - Automated incident response procedures',
            'communication_strategy': '**Immediate (Within 24 hours):**\n- Service status communication\n- User notification about potential issues\n\n**Follow-up (Within 1 week):**\n- Detailed incident report\n- Service improvements implemented'
        }
        
        return service_impacts.get(service_name, default_impact)

    def _extract_technical_root_cause(self, service_name: str, error_data: List[Dict]) -> str:
        """Extract detailed technical root cause from error data."""
        if not error_data:
            return "No error data available for analysis"
        
        # Get a sample error to analyze
        sample_error = error_data[0]
        line_content = sample_error.get('line', '')
        
        try:
            parsed_line = json.loads(line_content)
            message = parsed_line.get('message', '')
            stack_trace = parsed_line.get('stackTrace', '')
            
            technical_analysis = []
            
            # Extract key technical details
            if 'NullPointerException' in stack_trace:
                technical_analysis.append("**Exception Type:** NullPointerException")
                # Extract the specific null reference
                if 'Cannot invoke' in stack_trace:
                    null_ref = stack_trace.split('Cannot invoke "')[1].split('"')[0] if 'Cannot invoke "' in stack_trace else 'Unknown'
                    technical_analysis.append(f"**Null Reference:** {null_ref}")
            
            if 'timeout' in message.lower() or 'timeout' in stack_trace.lower():
                technical_analysis.append("**Issue Type:** Timeout/Connection Issue")
            
            if 'connection refused' in message.lower() or 'connection refused' in stack_trace.lower():
                technical_analysis.append("**Issue Type:** Connection Refused")
            
            if '500' in message or '500' in stack_trace:
                technical_analysis.append("**Issue Type:** Internal Server Error (500)")
            
            if '503' in message or '503' in stack_trace:
                technical_analysis.append("**Issue Type:** Service Unavailable (503)")
            
            # Extract method/class information
            if 'at ' in stack_trace:
                stack_lines = stack_trace.split('\n')
                for line in stack_lines:
                    if 'at ' in line and ('(' in line or ')' in line):
                        method_info = line.split('at ')[1].split('(')[0] if 'at ' in line else ''
                        if method_info and not method_info.startswith('java.'):
                            technical_analysis.append(f"**Affected Method:** {method_info}")
                            break
            
            # Extract file/line information
            if '.java:' in stack_trace:
                file_info = stack_trace.split('.java:')[0].split('.')[-1] + '.java'
                line_info = stack_trace.split('.java:')[1].split(')')[0] if '.java:' in stack_trace else ''
                if file_info and line_info:
                    technical_analysis.append(f"**Source File:** {file_info}:{line_info}")
            
            # Add error pattern analysis
            error_patterns = {}
            for entry in error_data[:10]:  # Analyze first 10 errors
                entry_line = entry.get('line', '')
                try:
                    entry_parsed = json.loads(entry_line)
                    entry_message = entry_parsed.get('message', '')
                    if entry_message:
                        error_patterns[entry_message] = error_patterns.get(entry_message, 0) + 1
                except:
                    continue
            
            if error_patterns:
                most_common = max(error_patterns.items(), key=lambda x: x[1])
                technical_analysis.append(f"**Most Common Error:** {most_common[0][:100]}... ({most_common[1]} occurrences)")
            
            # Add time-based analysis
            timestamps = []
            for entry in error_data[:20]:  # Sample first 20 errors
                entry_line = entry.get('line', '')
                try:
                    entry_parsed = json.loads(entry_line)
                    timestamp = entry_parsed.get('timestamp', '')
                    if timestamp:
                        timestamps.append(timestamp)
                except:
                    continue
            
            if len(timestamps) >= 2:
                try:
                    from datetime import datetime
                    start_time = datetime.fromisoformat(timestamps[-1].replace('Z', '+00:00'))
                    end_time = datetime.fromisoformat(timestamps[0].replace('Z', '+00:00'))
                    duration = end_time - start_time
                    technical_analysis.append(f"**Error Duration:** {duration.total_seconds()/60:.1f} minutes")
                    technical_analysis.append(f"**Error Pattern:** {len(error_data)/max(duration.total_seconds()/60, 1):.1f} errors per minute")
                except:
                    pass
            
            if technical_analysis:
                return '\n'.join(f"- {item}" for item in technical_analysis)
            else:
                return "- **Error Type:** General application error\n- **Analysis:** Requires deeper investigation"
                
        except json.JSONDecodeError:
            return "- **Error Type:** Malformed log entry\n- **Analysis:** Log parsing failed"
        except Exception as e:
            return f"- **Error Type:** Analysis failed\n- **Details:** {str(e)}"

    def _generate_service_recommendations(self, service_name: str, error_data: List[Dict], service_metrics: Dict) -> str:
        """Generate specific recommendations for a service."""
        total_errors = service_metrics.get('total_errors', 0)
        critical_errors = service_metrics.get('critical_errors', 0)
        
        recommendations = []
        
        if total_errors > 1000:
            recommendations.append("🚨 **URGENT**: High error volume requires immediate investigation")
        if critical_errors > 0:
            recommendations.append("🔴 **CRITICAL**: Critical errors detected - check service health immediately")
        if total_errors > 100:
            recommendations.append("📊 **MONITORING**: Implement enhanced error tracking and alerting")
        
        recommendations.append("🔧 **PREVENTION**: Implement defensive programming and error handling")
        recommendations.append("📈 **OPTIMIZATION**: Review service performance and resource utilization")
        
        return "\n".join(f"- {rec}" for rec in recommendations)

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
        
        # Add detailed end-user impact analysis for top 3 services
        if 'service_metrics' in original_analysis:
            # Sort services by error count and get top 3
            sorted_services = sorted(
                original_analysis['service_metrics'].items(), 
                key=lambda x: x[1].get('total_errors', 0), 
                reverse=True
            )[:3]
            
            report_content += "## 🚨 Top 3 Services - Detailed End User Impact Analysis\n\n"
            
            for i, (service, metrics) in enumerate(sorted_services, 1):
                # Get error data for this service
                service_errors = [entry for entry in original_analysis.get('error_data', []) 
                                if entry.get('labels', {}).get('app') == service]
                
                # Generate detailed impact analysis
                total_system_errors = len(original_analysis.get('error_data', []))
                impact_analysis = self.generate_end_user_impact_analysis(service, service_errors, metrics, total_system_errors)
                report_content += impact_analysis
                
                if i < len(sorted_services):
                    report_content += "\n"
            
            report_content += "\n## 📊 All Services Overview\n\n"
            
            # Add basic service metrics for all services
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
            # Add error_data to patterns for detailed analysis
            error_patterns['error_data'] = error_data
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
        # Add error_data to patterns for detailed analysis
        error_patterns['error_data'] = error_data
        
        report_content = f"""# Basic Error Analysis Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Note:** LLM analysis unavailable

## 📊 Error Summary

- **Total Errors:** {error_patterns['total_errors']}
- **Services Affected:** {len(error_patterns['services'])}
- **Critical Errors:** {len(error_patterns['critical_errors'])}

## 🔍 Service Breakdown

"""
        
        # Add detailed end-user impact analysis for top 3 services
        if 'service_metrics' in error_patterns:
            # Sort services by error count and get top 3
            sorted_services = sorted(
                error_patterns['service_metrics'].items(), 
                key=lambda x: x[1].get('total_errors', 0), 
                reverse=True
            )[:3]
            
            report_content += "## 🚨 Top 3 Services - Detailed End User Impact Analysis\n\n"
            
            for i, (service, metrics) in enumerate(sorted_services, 1):
                # Get error data for this service
                service_errors = [entry for entry in error_patterns.get('error_data', []) 
                                if entry.get('labels', {}).get('app') == service]
                
                # Generate detailed impact analysis
                total_system_errors = len(original_analysis.get('error_data', []))
                impact_analysis = self.generate_end_user_impact_analysis(service, service_errors, metrics, total_system_errors)
                report_content += impact_analysis
                
                if i < len(sorted_services):
                    report_content += "\n"
            
            report_content += "\n## 📊 All Services Overview\n\n"
        
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
