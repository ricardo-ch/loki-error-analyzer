#!/usr/bin/env python3
"""
Loki Error Analyzer
Fetches error logs from Loki and generates detailed markdown reports.
"""

import yaml
import json
import subprocess
import time
import signal
import sys
import os
import argparse
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re

class LokiErrorAnalyzer:
    def __init__(self, config_file='config.yaml', environment='dev'):
        """Initialize the analyzer with configuration."""
        self.environment = environment
        self.config = self.load_config(config_file)
        self.kubectl_process = None
        self.log_data = []
        
    def load_config(self, config_file):
        """Load configuration from YAML file and apply environment-specific settings."""
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            # Apply environment-specific configurations
            self.apply_environment_config(config)
            return config
            
        except FileNotFoundError:
            print(f"Configuration file {config_file} not found!")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"Error parsing configuration file: {e}")
            sys.exit(1)
    
    def apply_environment_config(self, config):
        """Apply environment-specific configuration overrides."""
        env_configs = {
            'dev': {
                'loki': {
                    'context': 'platform-chili',
                    'namespace': 'observability',
                    'service': 'loki-read'
                },
                'query': {
                    'org_id': 'dev-ricardo',
                    'limit': 100000,
                    'days_back': 1
                },
                'report': {
                    'title': 'Loki Error Analysis Report - DEV',
                    'organization': 'Ricardo Services Infrastructure - DEV'
                }
            },
            'prod': {
                'loki': {
                    'context': 'platform-chili',
                    'namespace': 'observability',
                    'service': 'loki-read'
                },
                'query': {
                    'org_id': 'prod-ricardo',
                    'limit': 500000,
                    'days_back': 1,
                    'start_date': None,  # Will be calculated dynamically
                    'end_date': None     # Will be calculated dynamically
                },
                'report': {
                    'title': 'Loki Error Analysis Report - PRODUCTION',
                    'organization': 'Ricardo Services Infrastructure - PRODUCTION'
                }
            }
        }
        
        if self.environment in env_configs:
            env_config = env_configs[self.environment]
            # Deep merge environment config
            self.merge_config(config, env_config)
            
            # Apply environment-specific time calculations
            self.apply_time_config(config)
            
            print(f"Applied {self.environment.upper()} environment configuration")
        else:
            print(f"Warning: Unknown environment '{self.environment}', using default config")
    
    def merge_config(self, base_config, env_config):
        """Deep merge environment config into base config."""
        for key, value in env_config.items():
            if key in base_config and isinstance(base_config[key], dict) and isinstance(value, dict):
                self.merge_config(base_config[key], value)
            else:
                base_config[key] = value
    
    def apply_time_config(self, config):
        """Apply environment-specific time configurations."""
        if self.environment == 'prod':
            # For production, set specific time range: previous day 7PM-10PM
            now = datetime.now()
            yesterday = now - timedelta(days=1)
            
            # Set start time to yesterday 7PM
            start_time = yesterday.replace(hour=19, minute=0, second=0, microsecond=0)
            # Set end time to yesterday 10PM
            end_time = yesterday.replace(hour=22, minute=0, second=0, microsecond=0)
            
            # Format for logcli (ISO format with Z suffix)
            config['query']['start_date'] = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            config['query']['end_date'] = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            print(f"Production time range: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')} UTC")
    
    def setup_loki_tunnel(self):
        """Set up kubectl port-forward to Loki."""
        print("Setting up Loki tunnel...")
        
        # Check if kubectl is available
        try:
            subprocess.run(['kubectl', 'version', '--client'], 
                         check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: kubectl is not available or not configured!")
            sys.exit(1)
        
        # Check if context exists
        try:
            result = subprocess.run(['kubectl', 'config', 'get-contexts'], 
                                  capture_output=True, text=True)
            if self.config['loki']['context'] not in result.stdout:
                print(f"Error: Kubernetes context '{self.config['loki']['context']}' not found!")
                print(f"Available contexts:")
                print(result.stdout)
                sys.exit(1)
        except subprocess.CalledProcessError:
            print("Error: Failed to check Kubernetes contexts!")
            sys.exit(1)
        
        # Start port-forward
        try:
            self.kubectl_process = subprocess.Popen([
                'kubectl', 'port-forward',
                f"--context={self.config['loki']['context']}",
                f"--namespace={self.config['loki']['namespace']}",
                f"service/{self.config['loki']['service']}",
                f"{self.config['loki']['local_port']}:{self.config['loki']['remote_port']}"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            print(f"Port-forward started (PID: {self.kubectl_process.pid})")
            
            # Wait for tunnel to be ready
            print(f"Waiting {self.config['loki']['readiness_timeout']} seconds for tunnel to be ready...")
            time.sleep(self.config['loki']['readiness_timeout'])
            
            # Additional delay as configured
            if self.config['loki']['tunnel_delay'] > 0:
                print(f"Additional delay: {self.config['loki']['tunnel_delay']} seconds")
                time.sleep(self.config['loki']['tunnel_delay'])
                
        except Exception as e:
            print(f"Error starting port-forward: {e}")
            sys.exit(1)
    
    def cleanup_tunnel(self):
        """Clean up kubectl port-forward process."""
        if self.kubectl_process:
            print("Cleaning up kubectl port-forward...")
            try:
                self.kubectl_process.terminate()
                self.kubectl_process.wait(timeout=self.config['cleanup']['shutdown_timeout'])
                print("Port-forward cleaned up successfully")
            except subprocess.TimeoutExpired:
                print("Force killing port-forward process...")
                self.kubectl_process.kill()
                self.kubectl_process.wait()
            except Exception as e:
                print(f"Error cleaning up port-forward: {e}")
    
    def fetch_logs(self):
        """Fetch logs from Loki using logcli."""
        print("Fetching logs from Loki...")
        
        # Build logcli command
        cmd = [
            'logcli',
            'query',
            f'--addr=http://localhost:{self.config["loki"]["local_port"]}',
            f'--org-id={self.config["query"]["org_id"]}',
            f'--limit={self.config["query"]["limit"]}',
            f'--output={self.config["query"]["output_format"]}',
            f'--since={self.config["query"]["days_back"] * 24}h'
        ]
        
        # Add custom date range if specified
        if 'start_date' in self.config['query'] and self.config['query']['start_date']:
            cmd.extend(['--from', self.config['query']['start_date']])
        if 'end_date' in self.config['query'] and self.config['query']['end_date']:
            cmd.extend(['--to', self.config['query']['end_date']])
        
        # Add query - use proper LogQL syntax
        cmd.append(f'{{stream="{self.config["query"]["stream"]}"}} |~ "{self.config["query"]["level"]}"')
        
        try:
            print(f"Executing: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Save raw logs with environment-specific filename
            output_file = f"{self.environment}_{self.config['query']['output_file']}"
            with open(output_file, 'w') as f:
                f.write(result.stdout)
            
            print(f"Logs saved to {output_file}")
            
            # Parse logs
            self.parse_logs(result.stdout)
            
        except subprocess.CalledProcessError as e:
            print(f"Error fetching logs: {e}")
            print(f"stderr: {e.stderr}")
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error: {e}")
            sys.exit(1)
    
    def parse_logs(self, log_content):
        """Parse log content and extract error information."""
        print("Parsing logs...")
        
        self.log_data = []
        for line in log_content.strip().split('\n'):
            if line.strip():
                try:
                    log_entry = json.loads(line)
                    # Extract and enrich log entry with parsed information
                    enriched_entry = self.enrich_log_entry(log_entry)
                    self.log_data.append(enriched_entry)
                except json.JSONDecodeError:
                    continue
        
        print(f"Parsed {len(self.log_data)} log entries")
    
    def enrich_log_entry(self, log_entry):
        """Enrich log entry with parsed information from labels and message."""
        enriched = log_entry.copy()
        
        # Extract metadata from labels
        labels = log_entry.get('labels', {})
        enriched['app'] = labels.get('app', 'unknown')
        enriched['container'] = labels.get('container', 'unknown')
        enriched['namespace'] = labels.get('namespace', 'unknown')
        enriched['pod'] = labels.get('pod', 'unknown')
        enriched['service_name'] = labels.get('service_name', 'unknown')
        enriched['node_name'] = labels.get('node_name', 'unknown')
        
        # Parse the actual log message
        line_content = log_entry.get('line', '')
        try:
            # Try to parse the line as JSON (structured logging)
            parsed_line = json.loads(line_content)
            enriched['log_level'] = parsed_line.get('level', 'unknown')
            enriched['log_message'] = parsed_line.get('message', '')
            enriched['log_timestamp'] = parsed_line.get('timestamp', '')
            enriched['source_file'] = parsed_line.get('source', {}).get('file', '')
            enriched['source_method'] = parsed_line.get('source', {}).get('method', '')
            enriched['stack_trace'] = parsed_line.get('stackTrace', '')
            enriched['meta'] = parsed_line.get('meta', {})
        except (json.JSONDecodeError, TypeError):
            # Fallback for non-JSON log lines
            enriched['log_level'] = 'unknown'
            enriched['log_message'] = line_content
            enriched['log_timestamp'] = ''
            enriched['source_file'] = ''
            enriched['source_method'] = ''
            enriched['stack_trace'] = ''
            enriched['meta'] = {}
        
        return enriched
    
    def categorize_errors(self):
        """Categorize errors based on patterns."""
        print("Categorizing errors...")
        
        error_categories = defaultdict(int)  # Changed to count instead of storing full entries
        
        for log_entry in self.log_data:
            # Get the actual error message and stack trace
            message = log_entry.get('log_message', '') or ''
            stack_trace = log_entry.get('stack_trace', '') or ''
            
            # Handle case where message might be a dict
            if isinstance(message, dict):
                message = str(message)
            if isinstance(stack_trace, dict):
                stack_trace = str(stack_trace)
            
            combined_text = f"{message} {stack_trace}".lower()
            
            # Check each category
            categorized = False
            for category, config in self.config['error_categories'].items():
                keywords = config['keywords']
                if any(keyword.lower() in combined_text for keyword in keywords):
                    error_categories[category] += 1
                    categorized = True
                    break
            
            if not categorized:
                # Default category for uncategorized errors
                error_categories['other'] += 1
        
        return error_categories
    
    def analyze_errors(self):
        """Analyze errors and generate insights."""
        print("Analyzing errors...")
        
        if not self.log_data:
            print("No log data to analyze!")
            return None
        
        # Basic statistics
        total_errors = len(self.log_data)
        
        # Error categorization
        try:
            error_categories = self.categorize_errors()
        except Exception as e:
            print(f"Error during categorization: {e}")
            # Create empty categories as fallback
            error_categories = defaultdict(list)
        
        # Service/Application breakdown with detailed metrics
        service_metrics = defaultdict(lambda: {
            'total_errors': 0,
            'unique_pods': set(),
            'error_types': defaultdict(int),
            'top_errors': Counter(),
            'namespaces': set(),
            'critical_errors': 0
        })
        
        for i, log_entry in enumerate(self.log_data):
            try:
                app = log_entry.get('app', 'unknown')
                service_metrics[app]['total_errors'] += 1
                service_metrics[app]['unique_pods'].add(log_entry.get('pod', 'unknown'))
                service_metrics[app]['namespaces'].add(log_entry.get('namespace', 'unknown'))
                
                # Categorize error type for this service
                message = log_entry.get('log_message', '') or ''
                stack_trace = log_entry.get('stack_trace', '') or ''
                
                # Handle case where message might be a dict
                if isinstance(message, dict):
                    message = str(message)
                if isinstance(stack_trace, dict):
                    stack_trace = str(stack_trace)
                
                combined_text = f"{message} {stack_trace}".lower()
                
                # Determine error type
                error_type = 'other'
                for category, config in self.config['error_categories'].items():
                    if any(keyword.lower() in combined_text for keyword in config['keywords']):
                        error_type = category
                        break
                
                service_metrics[app]['error_types'][error_type] += 1
                # Only count non-empty messages to avoid issues
                if message and len(message.strip()) > 0:
                    service_metrics[app]['top_errors'][message] += 1
                
                # Count critical errors (timeouts, connection failures, etc.)
                critical_keywords = ['timeout', 'connection refused', 'connection failed', 'eofexception', '503', '502', '500']
                if any(keyword in combined_text for keyword in critical_keywords):
                    service_metrics[app]['critical_errors'] += 1
            except Exception as e:
                print(f"Error processing log entry {i}: {e}")
                continue
        
        # Convert sets to counts for JSON serialization and filter low-impact services
        min_service_threshold = self.config['analysis']['thresholds']['min_service_errors']
        filtered_service_metrics = {}
        filtered_services = []
        
        for service, metrics in service_metrics.items():
            # Only include services that meet the minimum error threshold
            if metrics['total_errors'] >= min_service_threshold:
                metrics['unique_pods'] = len(metrics['unique_pods'])
                metrics['namespaces'] = list(metrics['namespaces'])
                metrics['top_errors'] = metrics['top_errors'].most_common(5)
                # Convert error_types defaultdict to regular dict
                metrics['error_types'] = dict(metrics['error_types'])
                filtered_service_metrics[service] = metrics
            else:
                filtered_services.append((service, metrics['total_errors']))
        
        # Update service_metrics to use filtered results
        service_metrics = filtered_service_metrics
        
        if self.config['analysis']['debug']:
            print(f"Filtered out {len(filtered_services)} services with low error counts (threshold: {min_service_threshold})")
            if filtered_services:
                print("Filtered services:", [f"{service}({count})" for service, count in filtered_services[:5]])
            print(f"Kept {len(service_metrics)} services that meet error threshold")
        
        # Time analysis
        time_errors = defaultdict(int)
        for log_entry in self.log_data:
            timestamp = log_entry.get('timestamp', '')
            if timestamp:
                try:
                    hour = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).hour
                    time_errors[hour] += 1
                except:
                    continue
        
        # Top error messages across all services (filtered by frequency)
        error_messages = Counter()
        min_error_threshold = self.config['analysis']['thresholds']['min_error_occurrences']
        
        for log_entry in self.log_data:
            message = log_entry.get('log_message', '') or ''
            # Handle case where message might be a dict
            if isinstance(message, dict):
                message = str(message)
            if message and len(message.strip()) > 0:
                error_messages[message] += 1
        
        # Filter out errors that don't meet the minimum threshold
        filtered_error_messages = Counter()
        filtered_out_errors = 0
        for message, count in error_messages.items():
            if count >= min_error_threshold:
                filtered_error_messages[message] = count
            else:
                filtered_out_errors += count
        
        if self.config['analysis']['debug']:
            print(f"Filtered out {filtered_out_errors} low-frequency errors (threshold: {min_error_threshold})")
            print(f"Kept {sum(filtered_error_messages.values())} errors that meet frequency threshold")
        
        # Critical errors analysis with frequency filtering
        critical_errors = []
        critical_error_counts = defaultdict(int)
        critical_error_samples = defaultdict(list)
        
        # First pass: count critical errors by message
        for log_entry in self.log_data:
            message = log_entry.get('log_message', '') or ''
            stack_trace = log_entry.get('stack_trace', '') or ''
            
            # Handle case where message might be a dict
            if isinstance(message, dict):
                message = str(message)
            if isinstance(stack_trace, dict):
                stack_trace = str(stack_trace)
            
            combined_text = f"{message} {stack_trace}".lower()
            
            critical_keywords = ['timeout', 'connection refused', 'connection failed', 'eofexception', '503', '502', '500']
            if any(keyword in combined_text for keyword in critical_keywords):
                # Use a normalized message for counting (first 100 chars to group similar errors)
                normalized_message = message[:100] if message else 'unknown'
                critical_error_counts[normalized_message] += 1
                critical_error_samples[normalized_message].append({
                    'app': log_entry.get('app', 'unknown'),
                    'message': message,
                    'pod': log_entry.get('pod', 'unknown'),
                    'namespace': log_entry.get('namespace', 'unknown'),
                    'timestamp': log_entry.get('timestamp', ''),
                    'source_file': log_entry.get('source_file', '')
                })
        
        # Second pass: only include critical errors that meet the minimum threshold
        min_critical_threshold = self.config['analysis']['thresholds']['min_critical_error_occurrences']
        filtered_out_critical = 0
        for normalized_message, count in critical_error_counts.items():
            if count >= min_critical_threshold:
                # Take the most recent sample for each error type
                sample = critical_error_samples[normalized_message][0]
                sample['occurrence_count'] = count
                critical_errors.append(sample)
            else:
                filtered_out_critical += count
        
        if self.config['analysis']['debug']:
            print(f"Filtered out {filtered_out_critical} low-frequency critical errors (threshold: {min_critical_threshold})")
            print(f"Kept {len(critical_errors)} critical error types that meet frequency threshold")
        
        # Namespace breakdown
        namespace_errors = defaultdict(int)
        for log_entry in self.log_data:
            namespace = log_entry.get('namespace', 'unknown')
            namespace_errors[namespace] += 1
        
        return {
            'total_errors': total_errors,
            'error_categories': error_categories,
            'service_metrics': dict(service_metrics),
            'time_errors': time_errors,
            'top_error_messages': filtered_error_messages.most_common(10),
            'critical_errors': critical_errors[:20],  # Top 20 critical errors
            'namespace_errors': dict(namespace_errors)
        }
    
    def generate_tldr(self, analysis):
        """Generate TLDR summary for CTO."""
        if not analysis:
            return "No data available for analysis."
        
        total_errors = analysis['total_errors']
        services_affected = len(analysis['service_metrics'])
        critical_errors = len(analysis['critical_errors'])
        
        # Get top 3 services by error count
        top_services = sorted(analysis['service_metrics'].items(), 
                            key=lambda x: x[1]['total_errors'], reverse=True)[:3]
        
        # Get error categories
        error_categories = analysis.get('error_categories', {})
        top_category = max(error_categories.items(), key=lambda x: x[1]) if error_categories else ("Unknown", 0)
        
        # Determine severity level
        if critical_errors > 100:
            severity = "🔴 CRITICAL"
            action = "Immediate action required - high number of critical errors detected"
        elif critical_errors > 20:
            severity = "🟡 WARNING"
            action = "Monitor closely - elevated error levels detected"
        else:
            severity = "🟢 STABLE"
            action = "System appears stable - continue monitoring"
        
        tldr = f"""**{severity}** - {total_errors:,} total errors across {services_affected} services

**Key Findings:**
- **Critical Errors:** {critical_errors} (timeouts, connection failures, 5xx)
- **Top Error Category:** {top_category[0]} ({top_category[1]:,} occurrences)
- **Most Affected Services:** {', '.join([f"{service} ({metrics['total_errors']:,} errors)" for service, metrics in top_services])}

**Recommendation:** {action}

**Next Steps:** Review detailed analysis below for specific service issues and remediation steps."""
        
        return tldr

    def generate_loki_queries(self, analysis):
        """Generate actionable Loki queries for root cause investigation."""
        if not analysis:
            return "No analysis data available for query generation."
        
        # Get time range for queries
        time_range = self._get_time_range_for_queries()
        
        # Base Grafana URL structure from config
        base_url = self.config['grafana']['base_url']
        datasource_uid = self.config['grafana']['datasource_uid']
        org_id = self.config['grafana']['org_id']
        
        queries = []
        
        # 1. Top error services investigation
        if analysis.get('service_metrics'):
            top_services = sorted(analysis['service_metrics'].items(), 
                                key=lambda x: x[1]['total_errors'], reverse=True)[:3]
            
            queries.append("### 🎯 Top Error Services Investigation")
            queries.append("")
            
            for i, (service, metrics) in enumerate(top_services, 1):
                # Generate service-specific error query
                service_query = f'{{stream="stdout", app="{service}"}} |~ "error"'
                grafana_url = self._build_grafana_url(base_url, datasource_uid, service_query, time_range, org_id)
                
                # Generate both URL formats
                simple_url = self._build_simple_grafana_url(base_url, datasource_uid, service_query, time_range, org_id)
                
                queries.append(f"#### {i}. {service} ({metrics['total_errors']:,} errors)")
                queries.append(f"**Loki Query:** `{service_query}`")
                queries.append(f"**Grafana Link (Complex):** [Open in Grafana]({grafana_url})")
                queries.append(f"**Grafana Link (Simple):** [Open in Grafana]({simple_url})")
                queries.append("")
                
                # Add critical errors for this service
                if metrics.get('critical_errors', 0) > 0:
                    critical_query = f'{{stream="stdout", app="{service}"}} |~ "(timeout|connection refused|connection failed|eofexception|503|502|500)"'
                    critical_url = self._build_grafana_url(base_url, datasource_uid, critical_query, time_range, org_id)
                    
                    critical_simple_url = self._build_simple_grafana_url(base_url, datasource_uid, critical_query, time_range, org_id)
                    
                    queries.append(f"**Critical Errors Query:** `{critical_query}`")
                    queries.append(f"**Critical Errors Link (Complex):** [Open in Grafana]({critical_url})")
                    queries.append(f"**Critical Errors Link (Simple):** [Open in Grafana]({critical_simple_url})")
                    queries.append("")
        
        # 2. Critical errors across all services
        if analysis.get('critical_errors'):
            queries.append("### 🚨 Critical Errors Investigation")
            queries.append("")
            
            # Group critical errors by type
            critical_types = {}
            for error in analysis['critical_errors']:
                error_type = self._categorize_critical_error(error['message'])
                if error_type not in critical_types:
                    critical_types[error_type] = []
                critical_types[error_type].append(error)
            
            for error_type, errors in critical_types.items():
                if error_type == "timeout":
                    query = '{stream="stdout"} |~ "timeout"'
                elif error_type == "connection":
                    query = '{stream="stdout"} |~ "(connection refused|connection failed)"'
                elif error_type == "http_5xx":
                    query = '{stream="stdout"} |~ "(503|502|500)"'
                elif error_type == "exception":
                    query = '{stream="stdout"} |~ "eofexception"'
                else:
                    query = '{stream="stdout"} |~ "error"'
                
                grafana_url = self._build_grafana_url(base_url, datasource_uid, query, time_range, org_id)
                
                queries.append(f"#### {error_type.replace('_', ' ').title()} Errors ({len(errors)} types)")
                queries.append(f"**Loki Query:** `{query}`")
                queries.append(f"**Grafana Link:** [Open in Grafana]({grafana_url})")
                queries.append("")
        
        # 3. Error pattern analysis
        if analysis.get('top_error_messages'):
            queries.append("### 🔍 Error Pattern Analysis")
            queries.append("")
            
            # Get top error patterns
            top_patterns = analysis['top_error_messages'][:5]
            
            for i, (pattern, count) in enumerate(top_patterns, 1):
                # Extract key terms from error message for query
                key_terms = self._extract_key_terms(pattern)
                if key_terms:
                    query = f'{{stream="stdout"}} |~ "({"|".join(key_terms)})"'
                    grafana_url = self._build_grafana_url(base_url, datasource_uid, query, time_range, org_id)
                    
                    queries.append(f"#### {i}. Pattern: {pattern[:50]}{'...' if len(pattern) > 50 else ''} ({count} occurrences)")
                    queries.append(f"**Loki Query:** `{query}`")
                    queries.append(f"**Grafana Link:** [Open in Grafana]({grafana_url})")
                    queries.append("")
        
        # 4. Time-based analysis
        queries.append("### ⏰ Time-based Error Analysis")
        queries.append("")
        
        # Peak error hours
        if analysis.get('time_errors'):
            peak_hours = sorted(analysis['time_errors'].items(), key=lambda x: x[1], reverse=True)[:3]
            
            for hour, count in peak_hours:
                # Create time range for specific hour
                hour_time_range = self._get_hour_specific_time_range(hour)
                query = '{stream="stdout"} |~ "error"'
                grafana_url = self._build_grafana_url(base_url, datasource_uid, query, hour_time_range)
                
                queries.append(f"#### Peak Error Hour: {hour:02d}:00 ({count} errors)")
                queries.append(f"**Loki Query:** `{query}`")
                queries.append(f"**Grafana Link:** [Open in Grafana]({grafana_url})")
                queries.append("")
        
        # 5. Namespace-specific analysis
        if analysis.get('namespace_errors'):
            queries.append("### 🏷️ Namespace-specific Analysis")
            queries.append("")
            
            top_namespaces = sorted(analysis['namespace_errors'].items(), 
                                  key=lambda x: x[1], reverse=True)[:3]
            
            for namespace, count in top_namespaces:
                query = f'{{stream="stdout", namespace="{namespace}"}} |~ "error"'
                grafana_url = self._build_grafana_url(base_url, datasource_uid, query, time_range, org_id)
                
                queries.append(f"#### {namespace} ({count} errors)")
                queries.append(f"**Loki Query:** `{query}`")
                queries.append(f"**Grafana Link:** [Open in Grafana]({grafana_url})")
                queries.append("")
        
        return "\n".join(queries)
    
    def _get_time_range_for_queries(self):
        """Get time range parameters for Grafana queries."""
        if 'start_date' in self.config['query'] and self.config['query']['start_date']:
            # Use the same time range as the analysis
            from_time = self.config['query']['start_date']
            to_time = self.config['query']['end_date'] if 'end_date' in self.config['query'] else None
        else:
            # Default to last 24 hours
            from datetime import datetime, timedelta
            now = datetime.now()
            yesterday = now - timedelta(days=1)
            from_time = yesterday.strftime('%Y-%m-%dT%H:%M:%SZ')
            to_time = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        return from_time, to_time
    
    def _get_hour_specific_time_range(self, hour):
        """Get time range for a specific hour."""
        from datetime import datetime, timedelta
        now = datetime.now()
        target_hour = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if target_hour > now:
            target_hour = target_hour - timedelta(days=1)
        
        start_time = target_hour
        end_time = target_hour + timedelta(hours=1)
        
        return start_time.strftime('%Y-%m-%dT%H:%M:%SZ'), end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    def _build_grafana_url(self, base_url, datasource_uid, query, time_range, org_id=1):
        """Build Grafana explore URL with query and time range."""
        from_time, to_time = time_range
        
        # Convert time to milliseconds
        from datetime import datetime
        from_time_ms = int(datetime.fromisoformat(from_time.replace('Z', '+00:00')).timestamp() * 1000)
        to_time_ms = int(datetime.fromisoformat(to_time.replace('Z', '+00:00')).timestamp() * 1000)
        
        # Build the JSON structure for the URL
        import json
        import urllib.parse
        
        # Create the query structure
        query_structure = {
            "52i": {
                "datasource": datasource_uid,
                "queries": [
                    {
                        "datasource": {
                            "type": "loki",
                            "uid": datasource_uid
                        },
                        "editorMode": "code",
                        "expr": query,
                        "queryType": "range",
                        "refId": "A",
                        "direction": "backward"
                    }
                ],
                "range": {
                    "from": str(from_time_ms),
                    "to": str(to_time_ms)
                }
            }
        }
        
        # Convert to JSON and URL encode
        query_json = json.dumps(query_structure)
        encoded_panes = urllib.parse.quote(query_json)
        
        # Build the final URL
        url = f"{base_url}?schemaVersion=1&panes={encoded_panes}&orgId={org_id}"
        
        return url
    
    def _build_simple_grafana_url(self, base_url, datasource_uid, query, time_range, org_id=1):
        """Build a simpler Grafana URL as fallback."""
        from_time, to_time = time_range
        
        # Convert time to milliseconds
        from datetime import datetime
        from_time_ms = int(datetime.fromisoformat(from_time.replace('Z', '+00:00')).timestamp() * 1000)
        to_time_ms = int(datetime.fromisoformat(to_time.replace('Z', '+00:00')).timestamp() * 1000)
        
        # URL encode the query
        import urllib.parse
        encoded_query = urllib.parse.quote(query)
        
        # Simple URL format
        simple_url = f"{base_url}?datasource={datasource_uid}&query={encoded_query}&from={from_time_ms}&to={to_time_ms}&orgId={org_id}"
        
        return simple_url
    
    def _categorize_critical_error(self, message):
        """Categorize critical error message."""
        message_lower = message.lower()
        if 'timeout' in message_lower:
            return "timeout"
        elif any(term in message_lower for term in ['connection refused', 'connection failed']):
            return "connection"
        elif any(term in message_lower for term in ['503', '502', '500']):
            return "http_5xx"
        elif 'eofexception' in message_lower:
            return "exception"
        else:
            return "other"
    
    def _extract_key_terms(self, message):
        """Extract key terms from error message for query building."""
        # Remove common words and extract meaningful terms
        import re
        
        # Clean up the message
        cleaned = re.sub(r'[^\w\s]', ' ', message.lower())
        words = cleaned.split()
        
        # Filter out common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'cannot', 'error', 'exception', 'failed', 'failure'}
        
        key_terms = [word for word in words if len(word) > 3 and word not in stop_words]
        
        # Return top 3 most relevant terms
        return key_terms[:3]

    def generate_report(self, analysis):
        """Generate markdown report."""
        print("Generating markdown report...")
        
        if not analysis:
            print("No analysis data to generate report!")
            return
        
        # Generate TLDR for CTO
        tldr = self.generate_tldr(analysis)
        
        # Get filtering thresholds for reporting
        thresholds = self.config['analysis']['thresholds']
        
        # Generate Loki queries for root cause analysis
        loki_queries = self.generate_loki_queries(analysis)
        
        report_content = f"""# {self.config['report']['title']}

**Organization:** {self.config['report']['organization']}  
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Environment:** {self.config['loki']['context']}

## 📋 TLDR for CTO

{tldr}

## 🚨 Executive Summary

- **Total Errors:** {analysis['total_errors']:,}
- **Analysis Period:** {self.config['query']['days_back']} days
- **Data Source:** Loki ({self.config['loki']['namespace']} namespace)
- **Services Affected:** {len(analysis['service_metrics'])} services
- **Namespaces Affected:** {len(analysis['namespace_errors'])} namespaces

## 🔍 Analysis Filtering Applied

This analysis focuses on significant errors and excludes low-frequency issues:
- **Minimum Error Occurrences:** {thresholds['min_error_occurrences']} (errors appearing fewer times are filtered out)
- **Minimum Critical Error Occurrences:** {thresholds['min_critical_error_occurrences']} (critical errors appearing fewer times are filtered out)
- **Minimum Service Errors:** {thresholds['min_service_errors']} (services with fewer errors are excluded)
- **Minimum Service Error Percentage:** {thresholds['min_service_error_percentage']*100:.1f}% (services representing less than this percentage of total errors are excluded)

## 🔍 Root Cause Investigation Queries

Use these Loki queries in Grafana for deeper investigation:

**Note:** If the Grafana links don't work due to URL parsing issues, you can manually:
1. Go to [Grafana Explore](https://grafana.ricardo.engineering/explore)
2. Select the Loki datasource (`PD805B64DBD608BC9`)
3. Copy and paste the Loki queries below
4. Set the time range to match your analysis period

{loki_queries}

## 🔥 Critical Issues Requiring Immediate Attention

"""
        
        # Add critical errors
        if analysis['critical_errors']:
            report_content += "### Most Critical Errors (Timeouts, Connection Failures, 5xx)\n\n"
            for i, error in enumerate(analysis['critical_errors'][:10], 1):
                occurrence_count = error.get('occurrence_count', 1)
                report_content += f"{i}. **{error['app']}** - {error['message'][:80]}{'...' if len(error['message']) > 80 else ''}\n"
                report_content += f"   - Pod: `{error['pod']}`\n"
                report_content += f"   - Namespace: `{error['namespace']}`\n"
                report_content += f"   - Time: {error['timestamp']}\n"
                report_content += f"   - Occurrences: {occurrence_count}\n"
                if error['source_file']:
                    report_content += f"   - Source: `{error['source_file']}`\n"
                report_content += "\n"
        else:
            report_content += "✅ No critical errors detected in the analysis period.\n\n"
        
        report_content += "## 📊 Service Health Dashboard\n\n"
        
        # Add service metrics
        sorted_services = sorted(analysis['service_metrics'].items(), 
                               key=lambda x: x[1]['total_errors'], reverse=True)
        
        for service, metrics in sorted_services[:15]:  # Top 15 services
            percentage = (metrics['total_errors'] / analysis['total_errors']) * 100
            critical_rate = (metrics['critical_errors'] / metrics['total_errors']) * 100 if metrics['total_errors'] > 0 else 0
            
            report_content += f"### {service}\n"
            report_content += f"- **Total Errors:** {metrics['total_errors']:,} ({percentage:.1f}% of all errors)\n"
            report_content += f"- **Critical Errors:** {metrics['critical_errors']:,} ({critical_rate:.1f}% of service errors)\n"
            report_content += f"- **Affected Pods:** {metrics['unique_pods']}\n"
            report_content += f"- **Namespaces:** {', '.join(metrics['namespaces'])}\n"
            
            # Top error types for this service
            if metrics['error_types']:
                report_content += f"- **Error Types:** {', '.join([f'{k}({v})' for k, v in sorted(metrics['error_types'].items(), key=lambda x: x[1], reverse=True)[:3]])}\n"
            
            # Top error messages for this service
            if metrics['top_errors']:
                report_content += f"- **Top Error:** {metrics['top_errors'][0][0][:60]}{'...' if len(metrics['top_errors'][0][0]) > 60 else ''} ({metrics['top_errors'][0][1]} times)\n"
            
            report_content += "\n"
        
        report_content += "## 🏷️ Error Categories Analysis\n\n"
        
        # Add error categories
        for category, config in self.config['error_categories'].items():
            if category in analysis['error_categories']:
                count = analysis['error_categories'][category]
                percentage = (count / analysis['total_errors']) * 100
                report_content += f"### {config['name']}\n"
                report_content += f"- **Count:** {count:,} ({percentage:.1f}%)\n"
                report_content += f"- **Keywords:** {', '.join(config['keywords'])}\n\n"
        
        report_content += "## 🌍 Namespace Breakdown\n\n"
        
        # Add namespace breakdown
        sorted_namespaces = sorted(analysis['namespace_errors'].items(), key=lambda x: x[1], reverse=True)
        for namespace, count in sorted_namespaces:
            percentage = (count / analysis['total_errors']) * 100
            report_content += f"- **{namespace}:** {count:,} errors ({percentage:.1f}%)\n"
        
        report_content += "\n## ⏰ Time Distribution\n\n"
        
        # Add time analysis
        sorted_times = sorted(analysis['time_errors'].items())
        for hour, count in sorted_times:
            percentage = (count / analysis['total_errors']) * 100
            report_content += f"- **{hour:02d}:00:** {count:,} errors ({percentage:.1f}%)\n"
        
        report_content += "\n## 🎯 Top Error Messages Across All Services\n\n"
        
        # Add top error messages
        for i, (message, count) in enumerate(analysis['top_error_messages'][:10], 1):
            report_content += f"{i}. **{message[:100]}{'...' if len(message) > 100 else ''}** ({count} occurrences)\n"
        
        if self.config['report']['include_recommendations']:
            report_content += "\n## 🛠️ Actionable Recommendations\n\n"
            
            # Generate specific recommendations based on the data
            high_error_services = [s for s, m in analysis['service_metrics'].items() 
                                 if m['total_errors'] > analysis['total_errors'] * 0.1]  # >10% of total errors
            
            if high_error_services:
                report_content += "### 🚨 Immediate Actions Required\n"
                report_content += f"- **High Error Rate Services:** {', '.join(high_error_services)}\n"
                report_content += "- Investigate these services immediately for potential outages or performance issues\n"
                report_content += "- Check service health endpoints and resource utilization\n"
                report_content += "- Review recent deployments for these services\n\n"
            
            critical_services = [s for s, m in analysis['service_metrics'].items() 
                               if m['critical_errors'] > 0]
            
            if critical_services:
                report_content += "### ⚡ Critical Error Services\n"
                report_content += f"- **Services with Critical Errors:** {', '.join(critical_services)}\n"
                report_content += "- These services have timeouts, connection failures, or 5xx errors\n"
                report_content += "- Check network connectivity, database connections, and external service dependencies\n"
                report_content += "- Review timeout configurations and retry policies\n\n"
            
            report_content += "### 📈 Long-term Improvements\n"
            report_content += "- Implement structured logging with correlation IDs for better error tracking\n"
            report_content += "- Set up automated alerting for critical error patterns\n"
            report_content += "- Create runbooks for common error scenarios\n"
            report_content += "- Implement circuit breakers for external service calls\n"
            report_content += "- Regular error analysis and trend monitoring\n\n"
        
        if self.config['report']['include_technical_details']:
            report_content += "## 🔧 Technical Details\n\n"
            report_content += f"- **Loki Endpoint:** http://localhost:{self.config['loki']['local_port']}\n"
            report_content += f"- **Query:** {self.config['query']['stream']} |~ \"{self.config['query']['level']}\"\n"
            report_content += f"- **Limit:** {self.config['query']['limit']:,} entries\n"
            report_content += f"- **Output Format:** {self.config['query']['output_format']}\n\n"
        
        report_content += f"\n---\n\n{self.config['report']['footer']}\n"
        
        # Write report with environment-specific filename
        report_file = f"{self.environment}_{self.config['analysis']['report_file']}"
        with open(report_file, 'w') as f:
            f.write(report_content)
        
        print(f"Report generated: {report_file}")
    
    def analyze_from_file(self, input_file):
        """Analyze logs from a local JSON file instead of fetching from Loki."""
        try:
            print(f"Loading logs from file: {input_file}")
            
            # Load the JSON file (handle NDJSON format)
            self.log_data = []
            with open(input_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            self.log_data.append(json.loads(line))
                        except json.JSONDecodeError as e:
                            print(f"Warning: Skipping invalid JSON line: {e}")
                            continue
            
            print(f"Loaded {len(self.log_data)} log entries from file")
            
            # Analyze the logs
            print("Analyzing logs...")
            analysis_results = self.analyze_errors()
            
            # Generate report
            print("Generating report...")
            self.generate_report(analysis_results)
            
            print(f"Analysis complete! Report saved to {self.environment}_{self.config['analysis']['report_file']}")
            
        except FileNotFoundError:
            print(f"Error: Input file {input_file} not found!")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON file: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Error during analysis: {e}")
            sys.exit(1)

    def run(self):
        """Main execution method."""
        try:
            print("Starting Loki Error Analyzer...")
            
            # Setup Loki tunnel
            self.setup_loki_tunnel()
            
            # Fetch logs
            self.fetch_logs()
            
            # Analyze errors
            analysis = self.analyze_errors()
            
            # Generate report
            self.generate_report(analysis)
            
            print("Analysis completed successfully!")
            
        except KeyboardInterrupt:
            print("\nAnalysis interrupted by user")
        except Exception as e:
            print(f"Error during analysis: {e}")
        finally:
            # Cleanup
            if self.config['cleanup']['auto_cleanup']:
                self.cleanup_tunnel()

def signal_handler(signum, frame):
    """Handle interrupt signals."""
    print("\nReceived interrupt signal. Cleaning up...")
    sys.exit(0)

def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description='Loki Error Analyzer - Fetch and analyze error logs from Loki',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 loki_error_analyzer.py --env dev
  python3 loki_error_analyzer.py --env prod
  python3 loki_error_analyzer.py --env dev --config custom_config.yaml
  python3 loki_error_analyzer.py --env prod --days 3 --limit 200000
  python3 loki_error_analyzer.py --env prod --time-range 7pm-10pm-yesterday
  python3 loki_error_analyzer.py --env prod --start-time "2024-01-15T19:00:00Z" --end-time "2024-01-15T22:00:00Z"
        """
    )
    
    parser.add_argument(
        '--env', '--environment',
        choices=['dev', 'prod'],
        default='dev',
        help='Environment to analyze (dev or prod). Default: dev'
    )
    
    parser.add_argument(
        '--config', '-c',
        default='config.yaml',
        help='Configuration file path. Default: config.yaml'
    )
    
    parser.add_argument(
        '--days', '-d',
        type=int,
        help='Number of days to look back (overrides config file)'
    )
    
    parser.add_argument(
        '--limit', '-l',
        type=int,
        help='Maximum number of log entries to fetch (overrides config file)'
    )
    
    parser.add_argument(
        '--level',
        help='Log level filter (overrides config file). Examples: "error", "warn", "(error|warn)"'
    )
    
    parser.add_argument(
        '--stream',
        help='Log stream filter (overrides config file). Examples: "stdout", "app=my-service"'
    )
    
    parser.add_argument(
        '--start-time',
        help='Start time for log query (overrides config file). Format: "YYYY-MM-DDTHH:MM:SSZ"'
    )
    
    parser.add_argument(
        '--end-time',
        help='End time for log query (overrides config file). Format: "YYYY-MM-DDTHH:MM:SSZ"'
    )
    
    parser.add_argument(
        '--time-range',
        choices=['7pm-10pm-yesterday', 'custom'],
        help='Predefined time range for production logs. 7pm-10pm-yesterday: Previous day 7PM-10PM'
    )
    
    parser.add_argument(
        '--input-file',
        help='Input JSON file to analyze instead of fetching from Loki'
    )
    
    args = parser.parse_args()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run analyzer
    analyzer = LokiErrorAnalyzer(config_file=args.config, environment=args.env)
    
    # Apply command line overrides
    if args.days:
        analyzer.config['query']['days_back'] = args.days
        print(f"Overriding days_back to {args.days}")
    
    if args.limit:
        analyzer.config['query']['limit'] = args.limit
        print(f"Overriding limit to {args.limit}")
    
    if args.level:
        analyzer.config['query']['level'] = args.level
        print(f"Overriding level to {args.level}")
    
    if args.stream:
        analyzer.config['query']['stream'] = args.stream
        print(f"Overriding stream to {args.stream}")
    
    if args.start_time:
        analyzer.config['query']['start_date'] = args.start_time
        print(f"Overriding start_time to {args.start_time}")
    
    if args.end_time:
        analyzer.config['query']['end_date'] = args.end_time
        print(f"Overriding end_time to {args.end_time}")
    
    if args.time_range:
        if args.time_range == '7pm-10pm-yesterday':
            # Calculate yesterday 7PM-10PM
            now = datetime.now()
            yesterday = now - timedelta(days=1)
            start_time = yesterday.replace(hour=19, minute=0, second=0, microsecond=0)
            end_time = yesterday.replace(hour=22, minute=0, second=0, microsecond=0)
            
            analyzer.config['query']['start_date'] = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            analyzer.config['query']['end_date'] = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            print(f"Applied time range: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')} UTC")
    
    print(f"Starting analysis for {args.env.upper()} environment...")
    
    if args.input_file:
        print(f"Using input file: {args.input_file}")
        analyzer.analyze_from_file(args.input_file)
    else:
        analyzer.run()

if __name__ == "__main__":
    main()
