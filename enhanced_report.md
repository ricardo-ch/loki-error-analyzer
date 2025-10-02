# Enhanced Loki Error Analysis Report

**Generated:** 2025-10-01 08:20:21 UTC  
**Enhanced with:** gpt-oss:latest

<details>
<summary><h2>🤖 AI-Powered Analysis</h2></summary>

**1. Root‑Cause Analysis (based on observable error patterns)**  

| Service | Dominant Error Pattern | Likely Root Cause (evidence‑based) |
|---------|------------------------|------------------------------------|
| **search‑query‑api‑articles** | 500‑level responses + Solr client exception (`org.apache.solr.client.solrj.impl.BaseHttpSolrC…`) | Solr cluster is unreachable or overloaded. The exception indicates a low‑level HTTP client failure, which usually points to network timeouts, node failures, or a corrupted Solr index. |
| **frontend‑mobile‑api‑v2** | *“context timeout”* + *“unsupported article sta…”* | The API is calling downstream services (likely Solr or a database) that are slower than the configured timeout. The “unsupported article sta…” error shows that the service is receiving an article status value that is not mapped in its domain model, suggesting a data‑consistency or schema drift issue. |
| **orders‑spa** | 400 and 409 responses | 400 indicates malformed requests (client‑side validation failure). 409 indicates a conflict (duplicate resource or state conflict). Both point to incorrect request payloads or race conditions in order creation/updates. |
| **legacy‑redirection‑app** | 404 responses | The app is attempting to redirect to a resource that no longer exists or is mis‑configured. This is a routing or configuration issue. |
| **Other services** | Majority of logs are generic “error” or “ERROR” entries (180 676 + 37 533). | Without per‑service breakdown, we cannot pinpoint the exact cause, but the high volume suggests widespread issues—likely a combination of upstream failures, timeout misconfigurations, or a common dependency (e.g., a shared database or cache). |

**Key observations**

* The **critical errors** are concentrated in two services: `search-query-api-articles` (Solr‑related) and `frontend-mobile-api-v2` (timeout).  
* The **top error messages** repeat the same patterns, indicating a systemic problem rather than isolated incidents.  
* The presence of both `error` and `ERROR` levels with similar messages suggests inconsistent logging levels across services.

---

**2. Impact Assessment (factual)**  

| Metric | Observation | Impact |
|--------|-------------|--------|
| **Error volume** | 224 418 total errors; 180 676 `error` + 37 533 `ERROR` | Large number of failed requests; likely high user‑visible failures (e.g., search not working, order creation failing). |
| **Critical errors** | 5 critical entries, all from `search-query-api-articles` or `frontend-mobile-api-v2` | Search functionality and mobile‑app listings are compromised, affecting a large portion of the user base. |
| **404/400/409** | Repeated in `legacy-redirection-app` and `orders‑spa` | Users may see broken links or order submission errors. |
| **Timeouts** | `frontend-mobile-api-v2` context timeout | Mobile app may hang or fail to load listings, degrading UX. |
| **Solr client errors** | `org.apache.solr.client.solrj.impl.BaseHttpSolrC…` | Search queries to the `articles` collection are failing; downstream services that rely on search results will also fail. |

**What we cannot determine**

* Exact number of affected users or requests per service.  
* Whether the errors are evenly distributed over time or clustered (e.g., during a spike).  
* The health status of the underlying infrastructure (CPU, memory, network).  

---

**3. Immediate Actions Required (actionable, evidence‑based)**  

| Service | Action | Rationale |
|---------|--------|-----------|
| **search‑query‑api‑articles** | 1. Run Solr health check (`/admin/health`). 2. Verify Solr node connectivity (ping, port 8983). 3. If nodes are down, restart Solr cluster or failover to standby. 4. Check Solr logs for index corruption or GC pauses. | The 500 + Solr client exception indicates a Solr outage or severe latency. |
| **frontend‑mobile‑api‑v2** | 1. Increase request timeout to downstream services (e.g., Solr, DB). 2. Profile the `getListing` call to identify slow operations. 3. Add retry logic with exponential back‑off for transient failures. 4. Validate that all article status values are mapped; add a default case or reject unsupported values. | Context timeouts and “unsupported article sta…” errors point to slow dependencies and data‑model drift. |
| **orders‑spa** | 1. Inspect request payloads causing 400/409 errors; add stricter validation. 2. Log the full request body for failed cases. 3. Review order state machine to prevent conflict (409) scenarios. | 400/409 errors are client‑side; better validation will reduce them. |
| **legacy‑redirection‑app** | 1. Verify routing table and target URLs. 2. Update or remove stale redirects. | 404 indicates broken links; fixing routing will restore functionality. |
| **General** | 1. Enable/verify centralized logging (e.g., ELK/Graylog) to correlate errors across services. 2. Set up alerts for >10 % error rate per minute. 3. Temporarily increase log level for affected services to capture more context. | Better observability will help identify root causes quickly. |

---

**4. Long‑Term Recommendations (strategic improvements)**  

| Area | Recommendation | Expected Benefit |
|------|----------------|------------------|
| **Observability** | Adopt a unified tracing system (e.g., OpenTelemetry) to see end‑to‑end request paths. | Faster root‑cause identification and correlation of distributed errors. |
| **Error Handling** | Standardize logging levels and message formats across services. | Easier automated parsing and alerting. |
| **Resilience** | Implement circuit breakers and bulkheads for critical dependencies (Solr, DB). | Prevent cascading failures when a dependency is slow or down. |
| **Data Consistency** | Enforce schema validation on all article status values; deprecate unsupported values gradually. | Reduce “unsupported article sta…” errors. |
| **Performance** | Profile and optimize slow endpoints; consider caching frequently accessed data (e.g., article listings). | Lower latency, fewer timeouts. |
| **Capacity Planning** | Monitor Solr cluster metrics (CPU, heap, GC) and scale horizontally before reaching failure thresholds. | Avoid future 500 errors due to resource exhaustion. |
| **Deployment** | Use canary releases for new API versions; monitor error rates before full rollout. | Early detection of regressions. |
| **Incident Response** | Create runbooks for Solr outages and mobile‑app timeouts; run tabletop exercises. | Faster recovery during real incidents. |

---

**5. Service Priority Ranking**  

*Ranking is based on the combination of error volume (from top error messages) and presence of critical errors.*

| Rank | Service | Evidence |
|------|---------|----------|
| **1** | `search-query-api-articles` | 5 critical errors (2 500s + 2 Solr client errors). High impact on search. |
| **2** | `frontend-mobile-api-v2` | 2 critical errors (context timeout + unsupported status). Affects mobile listings. |
| **3** | `orders-spa` | 2 top error messages (400 & 409). Likely high user impact on order flow. |
| **4** | `legacy-redirection-app` | 1 top error message (404). Affects link resolution. |
| **5** | Remaining services | No critical errors listed; however, the overall error count suggests they are still affected. Prioritization should be revisited once per‑service metrics are available. |

**Note:** The ranking assumes that the frequency of the top error messages correlates with overall error volume. If per‑service error counts become available, the ranking should be updated accordingly.

---

**Bottom line**

The logs point to a **Solr outage** and **mobile‑app timeout** as the most critical issues, followed by **request validation problems** in the order and redirection services. Immediate remediation should focus on restoring Solr and improving timeout handling, while long‑term changes should target observability, resilience, and data consistency to prevent recurrence.

</details>

---

<details>
<summary><h2>📊 Original Analysis Summary</h2></summary>

- **Total Errors:** 224418
- **Services Affected:** 139
- **Critical Errors:** 5

</details>

<details>
<summary><h2>🔍 Service Health Overview</h2></summary>

</details>

<details>
<summary><h2>🚨 Top 3 Services - Detailed End User Impact Analysis</h2></summary>

## 🚨 End User Impact Analysis: frontend-mobile-api-v2

### **📊 Scale of Impact**
- **Total Errors:** 51,733 (23.1% of all system errors)
- **Critical Errors:** 19251 (37.2% of service errors)
- **Error Rate:** ~14.4 errors per hour
- **Affected Pods:** 20 pods

### **🔍 Root Cause Analysis**
**Primary Error:** 1 error occurred:
	* error on registry when calling func defined at /home/runner/_work/frontend-mobile-api/frontend-mobile-api/pkg/listings/service.go:426: error in getListing: unsupported article status, value was: unsupported



**Technical Details:**
- **Most Common Error:** 1 error occurred:
	* error on registry when calling func defined at /home/runner/_work/frontend-mobi... (5 occurrences)
- **Error Duration:** 0.5 minutes
- **Error Pattern:** 51733.0 errors per minute

**Error Distribution:**
Registry function call failures in mobile API endpoints

### **💰 Business Impact Assessment**

#### **Direct User Impact:**
1. **🔴 Mobile App Functionality Disrupted**
   - Core mobile app features may be unavailable
   - Users cannot complete essential actions
   - **User experience degradation** for mobile users

2. **🔴 API Response Failures**
   - Mobile app requests failing or timing out
   - Inconsistent user experience across app features

#### **Indirect User Impact:**
1. **🔴 Mobile User Engagement Loss**
   - Users may abandon the app due to failures
   - Reduced mobile traffic and engagement

2. **🔴 Support Ticket Increase**
   - High volume of user complaints about app issues
   - Increased customer support workload

### **🎯 Severity Classification**

**🔴 CRITICAL** - Business Critical - Immediate action required
- **Financial Impact:** Potential revenue loss from mobile user abandonment
- **User Trust:** Mobile users may lose confidence in app reliability
- **Operational Impact:** High error volume indicates mobile infrastructure issues

### **⚡ Immediate Actions Required**

1. **🔧 API Stabilization**
   - Investigate registry function call failures
   - Implement proper error handling and fallbacks

2. **📱 Mobile App Health Check**
   - Verify mobile app functionality
   - Test critical user journeys

3. **🔄 Load Balancing Review**
   - Check API load balancing configuration
   - Verify service discovery and routing

### **📈 Long-term Recommendations**

1. **🛡️ Mobile API Resilience**
   - Implement circuit breakers for external calls
   - Add comprehensive error handling

2. **📊 Mobile Monitoring**
   - Set up mobile-specific error tracking
   - Implement user journey monitoring

3. **🔄 API Optimization**
   - Optimize registry function calls
   - Implement caching strategies

### **💬 User Communication Strategy**

**Immediate (Within 2 hours):**
- Mobile app status page update
- In-app notification about temporary issues

**Follow-up (Within 24 hours):**
- Detailed incident report
- App store update if needed
- User compensation for service disruption

---


## 🚨 End User Impact Analysis: marketplace-frontend-app

### **📊 Scale of Impact**
- **Total Errors:** 38,489 (17.2% of all system errors)
- **Critical Errors:** 1781 (4.6% of service errors)
- **Error Rate:** ~10.7 errors per hour
- **Affected Pods:** 104 pods

### **🔍 Root Cause Analysis**
**Primary Error:** getSearchData-searchSuggestions

**Technical Details:**
- **Issue Type:** Timeout/Connection Issue
- **Issue Type:** Internal Server Error (500)
- **Affected Method:** Function.from 
- **Most Common Error:** getAllCategoriesCounts... (4 occurrences)
- **Error Duration:** 3.4 minutes
- **Error Pattern:** 11262.4 errors per minute

**Error Distribution:**
Multiple error types detected: error, warn

### **💰 Business Impact Assessment**

#### **Direct User Impact:**
1. **🔴 Service Functionality Disrupted**
   - Core marketplace-frontend-app features may be unavailable
   - Users may experience service interruptions

2. **🔴 Performance Degradation**
   - Service may be responding slowly or inconsistently

#### **Indirect User Impact:**
1. **🔴 User Experience Impact**
   - Users may encounter errors when using the service
   - Potential loss of user confidence

2. **🔴 System Reliability Concerns**
   - High error volume indicates underlying issues

### **🎯 Severity Classification**

**🔴 CRITICAL** - Business Critical - Immediate action required
- **Financial Impact:** Potential revenue impact from service disruptions
- **User Trust:** Users may lose confidence in service reliability
- **Operational Impact:** High error volume requires investigation and resolution

### **⚡ Immediate Actions Required**

1. **🔧 Service Investigation**
   - Investigate root cause of errors
   - Check service health and dependencies

2. **🔄 Error Handling**
   - Implement proper error handling
   - Add monitoring and alerting

3. **📊 Performance Review**
   - Review service performance metrics
   - Check resource utilization

### **📈 Long-term Recommendations**

1. **🛡️ Service Resilience**
   - Implement circuit breakers and retry logic
   - Add comprehensive monitoring

2. **📊 Observability**
   - Set up detailed error tracking
   - Implement business metrics monitoring

3. **🔄 Process Improvements**
   - Regular service health checks
   - Automated incident response procedures

### **💬 User Communication Strategy**

**Immediate (Within 24 hours):**
- Service status communication
- User notification about potential issues

**Follow-up (Within 1 week):**
- Detailed incident report
- Service improvements implemented

---


## 🚨 End User Impact Analysis: marketplace-spa

### **📊 Scale of Impact**
- **Total Errors:** 34,517 (15.4% of all system errors)
- **Critical Errors:** 1861 (5.4% of service errors)
- **Error Rate:** ~9.6 errors per hour
- **Affected Pods:** 154 pods

### **🔍 Root Cause Analysis**
**Primary Error:** getCategories

**Technical Details:**
- **Most Common Error:** getSellerOffers... (2 occurrences)
- **Error Duration:** 4.4 minutes
- **Error Pattern:** 7863.1 errors per minute

**Error Distribution:**
Multiple error types detected: error, warn

### **💰 Business Impact Assessment**

#### **Direct User Impact:**
1. **🔴 Service Functionality Disrupted**
   - Core marketplace-spa features may be unavailable
   - Users may experience service interruptions

2. **🔴 Performance Degradation**
   - Service may be responding slowly or inconsistently

#### **Indirect User Impact:**
1. **🔴 User Experience Impact**
   - Users may encounter errors when using the service
   - Potential loss of user confidence

2. **🔴 System Reliability Concerns**
   - High error volume indicates underlying issues

### **🎯 Severity Classification**

**🔴 CRITICAL** - Business Critical - Immediate action required
- **Financial Impact:** Potential revenue impact from service disruptions
- **User Trust:** Users may lose confidence in service reliability
- **Operational Impact:** High error volume requires investigation and resolution

### **⚡ Immediate Actions Required**

1. **🔧 Service Investigation**
   - Investigate root cause of errors
   - Check service health and dependencies

2. **🔄 Error Handling**
   - Implement proper error handling
   - Add monitoring and alerting

3. **📊 Performance Review**
   - Review service performance metrics
   - Check resource utilization

### **📈 Long-term Recommendations**

1. **🛡️ Service Resilience**
   - Implement circuit breakers and retry logic
   - Add comprehensive monitoring

2. **📊 Observability**
   - Set up detailed error tracking
   - Implement business metrics monitoring

3. **🔄 Process Improvements**
   - Regular service health checks
   - Automated incident response procedures

### **💬 User Communication Strategy**

**Immediate (Within 24 hours):**
- Service status communication
- User notification about potential issues

**Follow-up (Within 1 week):**
- Detailed incident report
- Service improvements implemented

---

</details>


<details>
<summary><h2>🔍 Root Cause Investigation Queries</h2></summary>

Use these Loki queries in Grafana for deeper investigation:

Use these Loki queries in Grafana for deeper investigation:

**Note:** If the Grafana links don't work due to URL parsing issues, you can manually:
1. Go to [Grafana Explore](https://grafana.ricardo.engineering/explore)
2. Select the Loki datasource (`PD805B64DBD608BC9`)
3. Copy and paste the Loki queries below
4. Set the time range to match your analysis period

### 🎯 Top Error Services Investigation

#### 1. frontend-mobile-api-v2 (51,733 errors)
**Loki Query:** `{stream="stdout", app="frontend-mobile-api-v2", container!~"istio-proxy"} |= "error"`
**Grafana Link (Complex):** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22lgj%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20app%3D%5C%22frontend-mobile-api-v2%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C%3D%20%5C%22error%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)
**Grafana Link (Simple):** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22simple%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20app%3D%5C%22frontend-mobile-api-v2%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C%3D%20%5C%22error%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)

**Critical Errors Query:** `{stream="stdout", app="frontend-mobile-api-v2", container!~"istio-proxy"} |~ "(timeout|connection refused|connection failed|eofexception|503|502|500)"`
**Critical Errors Link (Complex):** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22lgj%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20app%3D%5C%22frontend-mobile-api-v2%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C~%20%5C%22%28timeout%7Cconnection%20refused%7Cconnection%20failed%7Ceofexception%7C503%7C502%7C500%29%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)
**Critical Errors Link (Simple):** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22simple%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20app%3D%5C%22frontend-mobile-api-v2%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C~%20%5C%22%28timeout%7Cconnection%20refused%7Cconnection%20failed%7Ceofexception%7C503%7C502%7C500%29%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)

#### 2. marketplace-frontend-app (38,489 errors)
**Loki Query:** `{stream="stdout", app="marketplace-frontend-app", container!~"istio-proxy"} |= "error"`
**Grafana Link (Complex):** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22lgj%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20app%3D%5C%22marketplace-frontend-app%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C%3D%20%5C%22error%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)
**Grafana Link (Simple):** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22simple%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20app%3D%5C%22marketplace-frontend-app%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C%3D%20%5C%22error%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)

**Critical Errors Query:** `{stream="stdout", app="marketplace-frontend-app", container!~"istio-proxy"} |~ "(timeout|connection refused|connection failed|eofexception|503|502|500)"`
**Critical Errors Link (Complex):** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22lgj%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20app%3D%5C%22marketplace-frontend-app%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C~%20%5C%22%28timeout%7Cconnection%20refused%7Cconnection%20failed%7Ceofexception%7C503%7C502%7C500%29%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)
**Critical Errors Link (Simple):** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22simple%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20app%3D%5C%22marketplace-frontend-app%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C~%20%5C%22%28timeout%7Cconnection%20refused%7Cconnection%20failed%7Ceofexception%7C503%7C502%7C500%29%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)

#### 3. marketplace-spa (34,517 errors)
**Loki Query:** `{stream="stdout", app="marketplace-spa", container!~"istio-proxy"} |= "error"`
**Grafana Link (Complex):** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22lgj%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20app%3D%5C%22marketplace-spa%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C%3D%20%5C%22error%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)
**Grafana Link (Simple):** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22simple%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20app%3D%5C%22marketplace-spa%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C%3D%20%5C%22error%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)

**Critical Errors Query:** `{stream="stdout", app="marketplace-spa", container!~"istio-proxy"} |~ "(timeout|connection refused|connection failed|eofexception|503|502|500)"`
**Critical Errors Link (Complex):** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22lgj%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20app%3D%5C%22marketplace-spa%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C~%20%5C%22%28timeout%7Cconnection%20refused%7Cconnection%20failed%7Ceofexception%7C503%7C502%7C500%29%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)
**Critical Errors Link (Simple):** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22simple%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20app%3D%5C%22marketplace-spa%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C~%20%5C%22%28timeout%7Cconnection%20refused%7Cconnection%20failed%7Ceofexception%7C503%7C502%7C500%29%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)

### 🚨 Critical Errors Investigation

#### Http 5Xx Errors (10 types)
**Loki Query:** `{stream="stdout", container!~"istio-proxy"} |~ "(503|502|500)"`
**Grafana Link:** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22lgj%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C~%20%5C%22%28503%7C502%7C500%29%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)

#### Timeout Errors (6 types)
**Loki Query:** `{stream="stdout", container!~"istio-proxy"} |~ "timeout"`
**Grafana Link:** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22lgj%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C~%20%5C%22timeout%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)

#### Other Errors (3 types)
**Loki Query:** `{stream="stdout", container!~"istio-proxy"} |= "error"`
**Grafana Link:** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22lgj%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C%3D%20%5C%22error%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)

#### Connection Errors (1 types)
**Loki Query:** `{stream="stdout", container!~"istio-proxy"} |~ "(connection refused|connection failed)"`
**Grafana Link:** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22lgj%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C~%20%5C%22%28connection%20refused%7Cconnection%20failed%29%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)

### 🔍 Error Pattern Analysis

#### 1. Pattern: Failed to export spans. Server is UNAVAILABLE. Mak... (21615 occurrences)
**Loki Query:** `{stream="stdout", container!~"istio-proxy"} |~ "(export|spans|server)"`
**Grafana Link:** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22lgj%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C~%20%5C%22%28export%7Cspans%7Cserver%29%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)

#### 2. Pattern: Request processing completed with status 500 (21028 occurrences)
**Loki Query:** `{stream="stdout", container!~"istio-proxy"} |~ "(request|processing|completed)"`
**Grafana Link:** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22lgj%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C~%20%5C%22%28request%7Cprocessing%7Ccompleted%29%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)

#### 3. Pattern: 1 error occurred:
	* error on registry when callin... (11032 occurrences)
**Loki Query:** `{stream="stdout", container!~"istio-proxy"} |~ "(occurred|registry|when)"`
**Grafana Link:** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22lgj%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C~%20%5C%22%28occurred%7Cregistry%7Cwhen%29%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)

#### 4. Pattern: getCategories (10705 occurrences)
**Loki Query:** `{stream="stdout", container!~"istio-proxy"} |~ "(getcategories)"`
**Grafana Link:** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22lgj%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C~%20%5C%22%28getcategories%29%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)

#### 5. Pattern: error building imaginary URL: NamedTransformationN... (9065 occurrences)
**Loki Query:** `{stream="stdout", container!~"istio-proxy"} |~ "(building|imaginary|namedtransformationnotfound)"`
**Grafana Link:** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22lgj%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C~%20%5C%22%28building%7Cimaginary%7Cnamedtransformationnotfound%29%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)

### ⏰ Time-based Error Analysis

#### Peak Error Hour: 20:00 (147678 errors)
**Loki Query:** `{stream="stdout", container!~"istio-proxy"} |= "error"`
**Grafana Link:** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22lgj%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C%3D%20%5C%22error%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759176000000%22%2C%20%22to%22%3A%20%221759179600000%22%7D%7D%7D&orgId=1)

#### Peak Error Hour: 21:00 (41903 errors)
**Loki Query:** `{stream="stdout", container!~"istio-proxy"} |= "error"`
**Grafana Link:** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22lgj%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C%3D%20%5C%22error%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759179600000%22%2C%20%22to%22%3A%20%221759183200000%22%7D%7D%7D&orgId=1)

#### Peak Error Hour: 22:00 (24275 errors)
**Loki Query:** `{stream="stdout", container!~"istio-proxy"} |= "error"`
**Grafana Link:** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22lgj%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C%3D%20%5C%22error%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759183200000%22%2C%20%22to%22%3A%20%221759186800000%22%7D%7D%7D&orgId=1)

### 🏷️ Namespace-specific Analysis

#### ricardo-services (183529 errors)
**Loki Query:** `{stream="stdout", namespace="ricardo-services", container!~"istio-proxy"} |= "error"`
**Grafana Link:** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22lgj%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20namespace%3D%5C%22ricardo-services%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C%3D%20%5C%22error%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)

#### unknown (36960 errors)
**Loki Query:** `{stream="stdout", namespace="unknown", container!~"istio-proxy"} |= "error"`
**Grafana Link:** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22lgj%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20namespace%3D%5C%22unknown%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C%3D%20%5C%22error%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)

#### data-intelligence (3611 errors)
**Loki Query:** `{stream="stdout", namespace="data-intelligence", container!~"istio-proxy"} |= "error"`
**Grafana Link:** [Open in Grafana](https://grafana.ricardo.engineering/explore?schemaVersion=1&panes=%7B%22lgj%22%3A%20%7B%22datasource%22%3A%20%22PD805B64DBD608BC9%22%2C%20%22queries%22%3A%20%5B%7B%22refId%22%3A%20%22A%22%2C%20%22expr%22%3A%20%22%7Bstream%3D%5C%22stdout%5C%22%2C%20namespace%3D%5C%22data-intelligence%5C%22%2C%20container%21~%5C%22istio-proxy%5C%22%7D%20%7C%3D%20%5C%22error%5C%22%5Cn%22%2C%20%22queryType%22%3A%20%22range%22%2C%20%22datasource%22%3A%20%7B%22type%22%3A%20%22loki%22%2C%20%22uid%22%3A%20%22PD805B64DBD608BC9%22%7D%2C%20%22editorMode%22%3A%20%22code%22%2C%20%22direction%22%3A%20%22backward%22%7D%5D%2C%20%22range%22%3A%20%7B%22from%22%3A%20%221759078800000%22%2C%20%22to%22%3A%20%221759093199000%22%7D%7D%7D&orgId=1)

</details>

---

<details>
<summary><h2>🚨 Critical Issues</h2></summary>

1. **search-query-api-articles** - Request processing completed with status 500...
   - Pod: `Unknown`
   - Time: Unknown

2. **search-query-api-articles** - Request to collection [articles] failed due to (500) org.apache.solr.client.solr...
   - Pod: `Unknown`
   - Time: Unknown

3. **search-query-api-articles** - Request processing completed with status 500...
   - Pod: `Unknown`
   - Time: Unknown

4. **search-query-api-articles** - Request to collection [articles] failed due to (500) org.apache.solr.client.solr...
   - Pod: `Unknown`
   - Time: Unknown

5. **frontend-mobile-api-v2** - context timeout...
   - Pod: `Unknown`
   - Time: Unknown


</details>

<details>
<summary><h2>📈 Recommendations</h2></summary>

Based on the AI analysis above, focus on the recommended actions and long-term improvements.

</details>

---

*This report was enhanced using local LLM analysis. For technical questions, contact the DevOps team.*
