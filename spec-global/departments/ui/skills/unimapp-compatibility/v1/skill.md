# UniApp Compatibility Skill

**Version**: 1.0
**Source**: Phase 5 (v1.2 Onboarding Pages)
**Status**: Production-Ready
**Maintained By**: UI/UX Team

## Overview

This skill document addresses the critical compatibility differences between UniApp and standard Vue 3, along with proven patterns for handling cross-platform event handling in component development. Essential for projects targeting H5, WeChat Mini-Programs, and Native Apps.

---

## The Core Challenge: Event Structure Differences

### Event Value Access

**UniApp Event Structure**:
```typescript
// UniApp events use e.detail.value
{
  detail: {
    value: 'user input'
  }
}
```

**Standard DOM Event Structure**:
```typescript
// Standard DOM events use e.target.value
{
  target: {
    value: 'user input'
  }
}
```

### Why This Matters

UniApp compiles to multiple platforms:
- **H5**: Standard browser environment (DOM events)
- **WeChat Mini-Program**: Custom runtime (UniApp events)
- **App**: Native wrappers (UniApp events)

Components must handle both structures seamlessly.

---

## The Fallback Pattern

### Standard Implementation

```typescript
const handleInput = (e: any) => {
  // Handle both UniApp events (e.detail.value) and standard DOM events (e.target.value)
  const rawValue = e.detail?.value ?? e.target?.value ?? ''

  // Use validation utilities
  const { valid, cleaned } = cleanAndValidatePhone(rawValue)

  // Update state
  localValue.value = cleaned
  emit('update:modelValue', cleaned)
  emit('validation', { valid, cleaned })
}
```

### Pattern Breakdown

1. **Optional Chaining**: `e.detail?.value` safely accesses UniApp structure
2. **Nullish Coalescing**: `??` falls back to DOM structure
3. **Final Fallback**: `?? ''` provides default empty string
4. **Type Safety**: Use `any` for event parameter to accommodate both types

---

## Platform-Specific Builds

### Conditional Compilation

UniApp supports platform-specific code blocks:

```typescript
// #ifdef MP-WEIXIN
// WeChat mini-program specific code
const BASE_URL = 'http://192.168.0.103:8080'
// #endif

// #ifndef MP-WEIXIN
// H5 and other platforms
const BASE_URL = import.meta.env.VITE_API_BASE_URL
// #endif

// #ifdef H5
// H5 specific code
window.addEventListener('resize', handleResize)
// #endif

// #ifndef H5
// Non-H5 platforms
uni.onWindowResize(handleResize)
// #endif
```

### Platform Detection

```typescript
// Runtime platform detection (for non-security decisions)
const getPlatform = (): string => {
  // #ifdef MP-WEIXIN
  return 'weixin'
  // #endif

  // #ifdef H5
  return 'h5'
  // #endif

  // #ifdef APP-PLUS
  return 'app'
  // #endif

  return 'unknown'
}
```

---

## Testing Strategy

### The Testing Challenge

**Problem**: Standard DOM tests don't validate UniApp event handling.

**Current State**:
```typescript
// Standard DOM test (works in browser)
wrapper.find('.phone-input-field').setValue('13800138000')
// This creates e.target.value, not e.detail.value
```

**Issue**: UniApp event structure (`e.detail.value`) not tested.

### UniApp Test Utilities

**Create**: `test-utils/unimapp-events.ts`

```typescript
/**
 * UniApp Event Mock Utilities
 * For testing UniApp component compatibility
 */

export interface UniAppInputEvent {
  detail: {
    value: string
  }
}

export interface UniAppChangeEvent {
  detail: {
    value: string
  }
}

export const createUniAppInputEvent = (value: string): UniAppInputEvent => ({
  detail: { value }
})

export const createUniChangeEvent = (value: string): UniAppChangeEvent => ({
  detail: { value }
})

export const triggerUniAppInput = (wrapper: any, value: string) => {
  const event = createUniAppInputEvent(value)
  wrapper.vm.handleInput(event)
}

export const triggerUniAppChange = (wrapper: any, value: string) => {
  const event = createUniChangeEvent(value)
  wrapper.vm.handleInput(event)
}
```

### Test Examples

**Standard DOM Test**:
```typescript
it('should handle DOM input event', () => {
  const wrapper = mount(PhoneInput, {
    props: { modelValue: '' }
  })

  wrapper.find('.phone-input-field').setValue('13800138000')

  expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['13800138000'])
})
```

**UniApp Event Test**:
```typescript
it('should handle UniApp input event', () => {
  const wrapper = mount(PhoneInput, {
    props: { modelValue: '' }
  })

  const event = createUniAppInputEvent('13800138000')
  wrapper.vm.handleInput(event)

  expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['13800138000'])
})
```

**Cross-Platform Test**:
```typescript
it('should handle both DOM and UniApp events', () => {
  const wrapper = mount(PhoneInput, {
    props: { modelValue: '' }
  })

  // Test DOM event
  wrapper.find('.phone-input-field').setValue('13800138000')
  expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['13800138000'])

  // Reset
  wrapper.emitted()['update:modelValue'] = []

  // Test UniApp event
  const uniEvent = createUniAppInputEvent('13900139000')
  wrapper.vm.handleInput(uniEvent)
  expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['13900139000'])
})
```

---

## Best Practices

### Event Handling

**DO**:
```typescript
const handleInput = (e: any) => {
  const rawValue = e.detail?.value ?? e.target?.value ?? ''
  // Process value
}
```

**DON'T**:
```typescript
const handleInput = (e: any) => {
  const rawValue = e.target.value  // Only works in H5
  // Process value
}
```

### Type Safety

**DO**:
```typescript
const handleInput = (e: any) => {
  // Use 'any' to accommodate both event types
  const value = e.detail?.value ?? e.target?.value ?? ''
}
```

**DON'T**:
```typescript
const handleInput = (e: Event) => {
  // Type too restrictive, won't work with UniApp
  const value = (e.target as HTMLInputElement).value
}
```

### Platform-Specific Code

**DO**:
```typescript
// Use conditional compilation for platform-specific code
// #ifdef MP-WEIXIN
// WeChat-specific code
// #endif
```

**DON'T**:
```typescript
// Don't use runtime detection for critical functionality
if (uni.getSystemInfoSync().platform === 'weixin') {
  // WeChat-specific code
}
```

---

## Common Issues & Solutions

### Issue: Events Not Firing in Mini-Program

**Symptom**: Input events work in H5 but not in WeChat mini-program.

**Cause**: Using `e.target.value` instead of fallback pattern.

**Solution**:
```typescript
const rawValue = e.detail?.value ?? e.target?.value ?? ''
```

### Issue: Tests Pass But App Fails

**Symptom**: Tests pass in browser but component doesn't work in mini-program.

**Cause**: Tests only simulate DOM events.

**Solution**: Add UniApp event tests:
```typescript
const event = createUniAppInputEvent('test value')
wrapper.vm.handleInput(event)
```

### Issue: Platform-Specific APIs Missing

**Symptom**: API works in H5 but not in mini-program.

**Cause**: Using browser-specific APIs.

**Solution**: Use UniApp APIs or conditional compilation:
```typescript
// #ifdef H5
window.addEventListener('resize', handler)
// #endif
// #ifndef H5
uni.onWindowResize(handler)
// #endif
```

---

## Event Handling Reference Table

| Event Type | UniApp Property | DOM Property | Fallback Pattern |
|------------|----------------|--------------|------------------|
| Input | `e.detail.value` | `e.target.value` | `e.detail?.value ?? e.target?.value` |
| Change | `e.detail.value` | `e.target.value` | `e.detail?.value ?? e.target?.value` |
| Focus | `e.detail` | `e.target` | `e.detail ?? e.target` |
| Blur | `e.detail` | `e.target` | `e.detail ?? e.target` |
| Click | `e.detail` | `e.target` | `e.detail ?? e.target` |

---

## Component Testing Checklist

- [ ] Standard DOM event tests pass
- [ ] UniApp event tests pass
- [ ] Fallback pattern implemented
- [ ] Type safety maintained
- [ ] Platform-specific builds tested
- [ ] Edge cases covered (empty, null, undefined)

---

## Quick Reference Card

```typescript
// Event Handling Pattern
const rawValue = e.detail?.value ?? e.target?.value ?? ''

// Conditional Compilation
// #ifdef MP-WEIXIN
// #endif

// Platform Detection
const platform = getPlatform()

// Test Utilities
const event = createUniAppInputEvent('value')
wrapper.vm.handleInput(event)
```

---

## Knowledge Sources

- **Phase 5 Knowledge**: `dev/dev/phase5/openspec/08-knowledge/02-unimapp-compatibility.md`
- **Implementation**:
  - `src/components/onboarding/PhoneInput.vue`
  - `src/components/onboarding/VerifyCodeInput.vue`
  - `src/components/onboarding/NumberStepper.vue`
- **Tests**:
  - All component test suites with cross-platform tests
- **Documentation**:
  - Phase 5 Retrospective
  - UniApp Official Documentation

---

**Last Updated**: 2026-02-08
**Phase**: Phase 5 (v1.2 Onboarding Pages)
**Status**: Production-Ready
