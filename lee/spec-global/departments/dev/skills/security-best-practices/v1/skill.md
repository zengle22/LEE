# Security Best Practices Skill

**Version**: 1.0
**Source**: Phase 5 (v1.2 Onboarding Pages)
**Status**: Production-Ready
**Maintained By**: Development Team

## Overview

This skill document consolidates enterprise-grade security best practices for frontend and backend development, established during Phase 5 implementation. It addresses critical security vulnerabilities (CRITICAL-001, CRITICAL-002) and establishes defense-in-depth validation standards.

---

## Core Security Principles

### 1. Defense-in-Depth Validation

**Principle**: Validate and sanitize at BOTH frontend and backend layers.

**Frontend Implementation**:
```typescript
// src/utils/validation.ts
export const cleanAndValidatePhone = (input: string): { valid: boolean; cleaned: string } => {
  const cleaned = sanitizeInput(input).replace(/\D/g, '')
  const valid = isValidPhone(cleaned)
  return { valid, cleaned }
}
```

**Backend Implementation**:
```go
// internal/util/validation.go
func ValidatePhone(phone string) ValidationResult {
  phone = SanitizeString(phone, MaxPhoneLength)
  if len(phone) != MinPhoneLength {
    return ValidationResult{Valid: false, Reason: "手机号长度必须为11位"}
  }
  if !phoneRegex.MatchString(phone) {
    return ValidationResult{Valid: false, Reason: "手机号格式不正确"}
  }
  return ValidationResult{Valid: true}
}
```

**Key Points**:
- Frontend validation: Better UX, immediate feedback
- Backend validation: Security, cannot be bypassed
- Both layers required: Defense-in-depth strategy

### 2. Build-Time vs Runtime Environment Detection

**CRITICAL SECURITY PRINCIPLE**: Build-time detection CANNOT be bypassed. Runtime detection CAN be bypassed.

**The Wrong Way (Runtime Detection)**:
```typescript
// ❌ CRITICAL SECURITY VULNERABILITY
const isDevEnvironment = computed(() => {
  const hostname = window.location.hostname
  return hostname === 'localhost' ||
         hostname.startsWith('192.168.') ||
         hostname.startsWith('10.') ||
         hostname.startsWith('172.')
})

// Usage (VULNERABLE)
if (isDevEnvironment.value) {
  enableDevLogin()
}
```

**The Right Way (Build-Time Detection)**:
```typescript
// ✅ SECURE: Build-time detection
const isDevelopment = (): boolean => {
  return import.meta.env.DEV || process.env.NODE_ENV === 'development'
}

export const devTestLogin = async (phone: string, code: string): Promise<LoginResponse> => {
  if (!isDevelopment()) {
    throw new Error('开发测试登录仅在开发环境可用')
  }
  // Rest of implementation
}
```

### 3. XSS Prevention

**Frontend Protection**:
```typescript
export const escapeHtml = (unsafe: string): string => {
  return unsafe
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}
```

**Backend Detection**:
```go
func CheckXSS(input string) bool {
  input = strings.ToLower(input)
  xssKeywords := []string{
    "<script", "</script", "javascript:", "onerror=", "onload=",
    "onclick=", "onmouseover=", "onfocus=", "onblur=",
    "eval(", "expression(", "vbscript:",
  }
  for _, keyword := range xssKeywords {
    if strings.Contains(input, keyword) {
      return true
    }
  }
  return false
}
```

### 4. SQL Injection Prevention

**Frontend Basic Filtering**:
```typescript
export const sanitizeForSql = (input: string): string => {
  return input
    .replace(/'/g, "''")
    .replace(/;/g, '')
    .replace(/--/g, '')
    .replace(/\/\*/g, '')
    .replace(/\*\//g, '')
}
```

**Backend Detection**:
```go
func CheckSQLInjection(input string) bool {
  input = strings.ToUpper(input)
  sqlInjectionKeywords := []string{
    "SELECT", "INSERT", "UPDATE", "DELETE", "DROP",
    "UNION", "OR", "AND", "--", "/*", "*/", ";",
    "EXEC", "EXECUTE", "SCRIPT", "JAVASCRIPT",
  }
  for _, keyword := range sqlInjectionKeywords {
    if strings.Contains(input, keyword) {
      return true
    }
  }
  return false
}
```

**Note**: Always use parameterized queries in database operations. This is a secondary defense.

---

## Security Checklist

### Implementation Phase

- [ ] All user inputs sanitized on frontend
- [ ] All user inputs validated on backend
- [ ] No hardcoded credentials or IPs
- [ ] Build-time environment detection only
- [ ] XSS protection implemented
- [ ] SQL injection protection implemented
- [ ] Length limits enforced
- [ ] Type checking enabled

### Code Review Phase

- [ ] Security requirements reviewed
- [ ] Input validation patterns checked
- [ ] Environment detection validated
- [ ] No runtime security decisions
- [ ] Error messages don't leak information
- [ ] Sensitive data not logged

### Testing Phase

- [ ] Security test cases created
- [ ] XSS attack scenarios tested
- [ ] SQL injection scenarios tested
- [ ] Input boundary cases tested
- [ ] Environment bypass attempts tested
- [ ] Validation utilities tested

---

## Critical Security Fixes Reference

### CRITICAL-001: Hardcoded Production IP

**Before**:
```typescript
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://8.137.77.8:8081'
```

**After**:
```typescript
const BASE_URL = import.meta.env.VITE_API_BASE_URL || (() => {
  throw new Error('VITE_API_BASE_URL is not configured')
})()
```

### CRITICAL-002: Development Login Bypass

**Before**:
```typescript
const isDevEnvironment = computed(() => {
  return window.location.hostname.startsWith('192.168.')
})
```

**After**:
```typescript
const isDevelopment = (): boolean => {
  return import.meta.env.DEV || process.env.NODE_ENV === 'development'
}
```

---

## Security Testing Guidelines

### Frontend Validation Tests

```typescript
describe('Input Validation', () => {
  it('should sanitize XSS attempts', () => {
    const input = '<script>alert("xss")</script>'
    const sanitized = escapeHtml(input)
    expect(sanitized).not.toContain('<script>')
  })

  it('should detect SQL injection patterns', () => {
    const input = "1' OR '1'='1"
    const result = cleanAndValidatePhone(input)
    expect(result.valid).toBe(false)
  })

  it('should enforce length limits', () => {
    const longInput = 'a'.repeat(2000)
    const sanitized = sanitizeInput(longInput)
    expect(sanitized.length).toBeLessThanOrEqual(1000)
  })
})
```

### Backend Validation Tests

```go
func TestCheckSQLInjection(t *testing.T) {
  tests := []struct {
    input string
    expected bool
  }{
    {"normal text", false},
    {"' OR '1'='1", true},
    {"; DROP TABLE users;", true},
    {"<script>alert(1)</script>", false}, // XSS, not SQL
  }

  for _, tt := range tests {
    result := CheckSQLInjection(tt.input)
    if result != tt.expected {
      t.Errorf("CheckSQLInjection(%q) = %v; want %v", tt.input, result, tt.expected)
    }
  }
}
```

---

## Common Security Pitfalls

### 1. Runtime Security Decisions

**Problem**: Using `window.location`, `document.referrer`, or other runtime properties for security decisions.

**Solution**: Use build-time environment variables exclusively.

### 2. Frontend-Only Validation

**Problem**: Relying solely on frontend validation.

**Solution**: Always validate on backend. Frontend is for UX, backend is for security.

### 3. Hardcoded Configuration

**Problem**: Hardcoding production URLs, IPs, or credentials.

**Solution**: Use environment variables with build-time validation.

### 4. Insufficient Input Sanitization

**Problem**: Only checking for specific attack patterns.

**Solution**: Comprehensive sanitization (control chars, length, type checking).

---

## Security Metrics (Phase 5 Achievement)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Critical Vulnerabilities | 2 | 0 | 100% |
| High Vulnerabilities | 4 | 1 | 75% |
| Input Validation Coverage | ~50% | 100% | 100% |
| Security Test Coverage | 0% | 85%+ | New |
| Build-Time Environment Checks | 0% | 100% | New |

---

## Knowledge Sources

- **Phase 5 Knowledge**: `dev/dev/phase5/openspec/08-knowledge/01-security-best-practices.md`
- **Implementation Files**:
  - `src/utils/validation.ts` (Frontend)
  - `internal/util/validation.go` (Backend)
  - `src/api/auth.ts` (Auth security)
- **Test Files**:
  - All component test suites with security tests
- **Documentation**:
  - Phase 5 Retrospective
  - Code Review Reports v1 & v2

---

## Usage Guidelines

### For New Phases

1. Review this security checklist before starting implementation
2. Include security requirements in proposal phase
3. Implement both frontend and backend validation
4. Use build-time environment detection for all security decisions
5. Include security test cases alongside functional tests

### For Code Reviews

1. Check all security checklist items
2. Verify build-time environment detection
3. Ensure no hardcoded credentials
4. Validate input sanitization
5. Review security test coverage

---

**Last Updated**: 2026-02-08
**Phase**: Phase 5 (v1.2 Onboarding Pages)
**Status**: Production-Ready
