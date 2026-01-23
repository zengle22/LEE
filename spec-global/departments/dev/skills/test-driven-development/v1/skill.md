# Test-Driven Development Skill v1.0

> **技能类型**: 确定性能力 (方法论)
> **无决策**: 提供 TDD 方法步骤，不判断何时使用

## 概述

提供 Test-First 开发方法的标准步骤和实践模式。

## TDD 循环

```
Red → Green → Refactor
  ↑________________|
```

### 1. Red: 写失败的测试

```typescript
// 先写测试
describe('UserAuth', () => {
  it('should authenticate valid user', async () => {
    const result = await auth.login('user@test.com', 'password');
    expect(result.success).toBe(true);
    expect(result.token).toBeDefined();
  });
});
```

### 2. Green: 写最小实现

```typescript
// 写最小代码使测试通过
async function login(email: string, password: string) {
  const user = await findUser(email);
  if (user && verify(password, user.hash)) {
    return { success: true, token: generateToken(user) };
  }
  return { success: false };
}
```

### 3. Refactor: 重构优化

```typescript
// 优化代码结构，保持测试通过
class AuthService {
  async login(credentials: Credentials): Promise<AuthResult> {
    const user = await this.userRepo.findByEmail(credentials.email);
    return user?.verifyPassword(credentials.password)
      ? AuthResult.success(this.tokenService.generate(user))
      : AuthResult.failure();
  }
}
```

## 测试类型层次

```
        /\
       /  \  E2E Tests (少)
      /----\
     /      \  Integration Tests
    /--------\
   /          \  Unit Tests (多)
  /______________\
```

### Unit Test 模式

```typescript
// 隔离测试，Mock 外部依赖
describe('PasswordValidator', () => {
  it('should require minimum 8 characters', () => {
    expect(validate('short')).toBe(false);
    expect(validate('longpassword')).toBe(true);
  });
});
```

### Integration Test 模式

```typescript
// 测试组件集成
describe('UserRegistration', () => {
  it('should create user and send email', async () => {
    const result = await register({ email: 'new@test.com' });
    expect(await userRepo.exists('new@test.com')).toBe(true);
    expect(emailService.sent).toContain('new@test.com');
  });
});
```

## 场景设计 (Given-When-Then)

```typescript
describe('Shopping Cart', () => {
  it('should calculate total with discount', () => {
    // Given
    const cart = new Cart();
    cart.add(item({ price: 100 }));
    cart.applyCoupon('10OFF');

    // When
    const total = cart.calculateTotal();

    // Then
    expect(total).toBe(90);
  });
});
```

## 边界测试清单

- [ ] 空值 / null / undefined
- [ ] 空数组 / 空字符串
- [ ] 最小值 / 最大值
- [ ] 边界值 ± 1
- [ ] 特殊字符
- [ ] 并发访问
- [ ] 超时场景

## Mock 策略

```typescript
// 外部服务 Mock
const mockPaymentGateway = {
  charge: jest.fn().mockResolvedValue({ id: 'tx_123' })
};

// 时间 Mock
jest.useFakeTimers();
jest.setSystemTime(new Date('2026-01-08'));

// 网络 Mock
nock('https://api.example.com')
  .get('/users/1')
  .reply(200, { id: 1, name: 'Test' });
```

## 覆盖率目标

| 指标 | 最低要求 | 推荐目标 |
|------|---------|---------|
| Statements | 80% | 90% |
| Branches | 70% | 85% |
| Functions | 80% | 90% |
| Lines | 80% | 90% |

## 约束

- ❌ 不判断测试是否足够
- ❌ 不决定测试优先级
- ❌ 不修改测试策略
- ✅ 只提供方法步骤
- ✅ 只提供代码模式
