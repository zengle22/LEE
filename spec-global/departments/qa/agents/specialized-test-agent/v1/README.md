# Specialized Test Agent v1.0

专项测试用例设计 Agent - 负责设计性能、安全和可访问性专项测试用例。

## Overview

The Specialized Test Agent (`agent.qa.specialized_test_agent`) designs comprehensive non-functional test cases covering:
- **Performance Testing**: Load, stress, latency, and scalability tests
- **Security Testing**: Authentication, authorization, and OWASP Top 10 vulnerability tests
- **Accessibility Testing**: WCAG compliance, screen reader, and keyboard navigation tests

## Agent Details

- **Agent ID**: `agent.qa.specialized_test_agent`
- **Version**: 1.0.0
- **Owner**: qa-specialized
- **Location**: `E:/ai/LEE/spec-global/departments/qa/agents/specialized-test-agent/v1/`

## Responsibilities

### Owns
- Performance test case design (load, stress, latency, scalability)
- Security test case design (authentication, authorization, OWASP Top 10)
- Accessibility test case design (WCAG, screen readers, keyboard navigation)

### Does Not Own
- Functional test case design (owned by `test-case-creator`)
- Test execution (owned by various test executors)
- Performance benchmark setting (owned by `tech-architect`)
- Security policy making (owned by `secops`)
- UI design (owned by `ui-designer`)

## Inputs

1. **Technical Architecture Document** (`frozen-technical-architecture-contract/v1/schema.json`)
   - Technology stack and components
   - System architecture and integration points
   - Performance-critical components
   - Security-sensitive data flows

2. **Test Case Contract** (`test-case-contract/v1/schema.json`)
   - Feature mapping matrix
   - Functional test cases
   - Component inventory

3. **UI Contract** (`ui-page-contract/v1/schema.json`) - Optional
   - UI components and interactions
   - State management
   - Accessibility requirements

## Outputs

1. **Specialized Test Contract** (`specialized-test-contract/v1/schema.json`)
   - Performance test suites
   - Security test suites
   - Accessibility test suites
   - Risk matrices
   - Tool recommendations

2. **Markdown Test Plan**
   - Human-readable test plan
   - Test coverage analysis
   - Execution guidelines

## Test Types

### Performance Tests

| Type | Description | Key Metrics |
|------|-------------|-------------|
| Load Test | Simulate expected user load | Response time, throughput, error rate |
| Stress Test | Push system beyond limits | Breaking point, recovery time |
| Latency Test | Measure response times | p50, p95, p99 percentiles |
| Scalability Test | Validate growth capability | Concurrent users, data volume |
| Endurance Test | Long-term stability | Memory leaks, resource utilization |
| Spike Test | Sudden load changes | Recovery time, system stability |

### Security Tests

Covering OWASP Top 10 (2021):
- A01: Broken Access Control
- A02: Cryptographic Failures
- A03: Injection
- A04: Insecure Design
- A05: Security Misconfiguration
- A06: Vulnerable and Outdated Components
- A07: Identification and Authentication Failures
- A08: Software and Data Integrity Failures
- A09: Security Logging and Monitoring Failures
- A10: Server-Side Request Forgery (SSRF)

### Accessibility Tests

Following WCAG 2.1/2.2:
- **Perceivable**: Text alternatives, time-based media, adaptability, distinguishability
- **Operable**: Keyboard accessible, enough time, seizures, navigable
- **Understandable**: Readable, predictable, input assistance
- **Robust**: Compatible with assistive technologies

Test methods:
- Automated tools (axe, WAVE, Lighthouse)
- Screen readers (NVDA, JAWS, VoiceOver)
- Keyboard-only navigation
- Color contrast analysis

## Workflow

1. **Input Validation**: Verify required contracts are available and complete
2. **Architecture Analysis**: Identify performance, security, and accessibility risks
3. **Performance Test Design**: Design load, stress, latency, and scalability tests
4. **Security Test Design**: Design authentication, authorization, and OWASP Top 10 tests
5. **Accessibility Test Design**: Design WCAG compliance and assistive technology tests
6. **Test Detailing**: Define test data, procedures, and success criteria
7. **Recommendation Generation**: Provide tools, environment, and automation suggestions
8. **Output Generation**: Generate JSON contract and Markdown documentation

## Quality Standards

### Performance Testing
- Each test case must define clear performance metrics
- Must include load models (concurrent users, RPS, data volume)
- Must define success/failure criteria
- Must provide monitoring and measurement recommendations
- Must consider normal, peak, and extreme scenarios

### Security Testing
- Must cover OWASP Top 10 relevant vulnerability types
- Each test case must define attack vector
- Must provide validation method (without causing harm)
- Must include authentication and authorization tests
- Must provide security remediation suggestions

### Accessibility Testing
- Must cover WCAG 2.1/2.2 AA level requirements
- Must include screen reader tests (NVDA, JAWS, VoiceOver)
- Must include keyboard navigation tests
- Must include color contrast tests
- Must consider different browser and device combinations

## Tool Recommendations

### Performance Testing
- **JMeter**: Load and performance testing
- **k6**: Modern load testing with JavaScript
- **Gatling**: High-performance load testing
- **Locust**: Python-based load testing
- **Artillery**: Node.js load testing

### Security Testing
- **OWASP ZAP**: Free security scanner
- **Burp Suite**: Professional security testing
- **SQLMap**: SQL injection testing
- **Nmap**: Network scanning
- **Metasploit**: Penetration testing framework

### Accessibility Testing
- **axe DevTools**: Automated accessibility testing
- **WAVE**: Web accessibility evaluation tool
- **Lighthouse**: Chrome accessibility audits
- **NVDA**: Free screen reader (Windows)
- **JAWS**: Commercial screen reader
- **VoiceOver**: Built-in screen reader (macOS/iOS)

## File Structure

```
specialized-test-agent/
├── v1/
│   ├── agent.yaml              # Agent specification
│   ├── README.md               # This file
│   └── contracts/
│       └── specialized-test-contract/
│           └── v1/
│               └── schema.json # Output contract schema
```

## Usage Example

```bash
# Invoke the agent with required inputs
agent run agent.qa.specialized_test_agent \
  --input architecture=./contracts/architecture.json \
  --input test_cases=./contracts/test-cases.json \
  --input ui_contract=./contracts/ui-contract.json \
  --output ./output/specialized-tests/
```

## Validation

The agent includes smoke tests that verify:
- Performance test suites are generated with proper metrics
- Security test suites cover OWASP Top 10 categories
- Accessibility test suites cover WCAG criteria
- All test cases have unique IDs and proper structure

## Version History

### v1.0.0 (2026-02-04)
- Initial version of Specialized Test Agent
- Support for performance testing (load, stress, latency, scalability)
- Support for security testing (OWASP Top 10, authentication, authorization)
- Support for accessibility testing (WCAG, screen readers, keyboard navigation)
- Risk matrix generation
- Test recommendations and tool suggestions

## Related Agents

- **test-case-creator**: Creates functional test cases
- **bug-manager**: Manages bug lifecycle
- **smoke-test-executor**: Executes smoke tests
- **system-test-executor**: Executes system tests
- **e2e-test-executor**: Executes end-to-end tests

## Compliance

This agent helps ensure compliance with:
- **SOC 2**: Security and availability testing
- **GDPR**: Data protection and privacy testing
- **PCI DSS**: Payment card security testing
- **WCAG 2.1/2.2**: Web content accessibility
- **ISO 27001**: Information security management

## Contact

For questions or issues related to this agent, please contact the QA team or open an issue in the specification repository.
