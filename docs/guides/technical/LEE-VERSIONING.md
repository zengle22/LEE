# LEE 版本号规则

本文档定义 `lee-framework` 的统一版本规则，适用于本地开发、CI 构建、候选发布和正式发布。

## 目标

- 让 `lee --version`、`.lee/lee.lock`、包版本、发布 tag 保持一致
- 区分开发基线版本、候选构建版本、正式发布版本
- 支持目标项目按版本升级和回滚

## 规则

### 1. 基线版本

基线版本写在 [pyproject.toml](/E:/ai/LEE/pyproject.toml)：

```toml
version = "0.2.0"
```

含义：

- 表示当前主线开发的下一个发布基线
- 只由维护者在进入新迭代时手动提升

### 2. 候选版本

`main` 或内部构建产物使用候选版本：

```text
0.2.0.devYYYYMMDD+<short_sha>
```

示例：

```text
0.2.0.dev20260310+7899f86
```

规则：

- `0.2.0` 来自基线版本
- `devYYYYMMDD` 表示构建日期
- `+short_sha` 表示源码提交

用途：

- 内部验证
- 测试环境安装
- 目标项目试用

### 3. 正式版本

正式版本必须是语义化版本：

```text
X.Y.Z
```

对应 Git tag：

```text
vX.Y.Z
```

示例：

```text
v0.3.0
```

规则：

- tag 可以带 `v`
- 包版本不带 `v`
- 只有 tag 版本才视为正式 release

## 命令面

CLI 顶层提供：

```bash
lee --version
lee -v
```

输出当前安装包版本，用于目标项目升级后的确认。

## 适用约束

- 不使用 `latest`、`main-snapshot` 这类不可审计版本名
- 不直接把 Git branch 名作为包版本
- 不在目标项目里依赖源码目录推断版本

## 推荐流程

1. 在 [pyproject.toml](/E:/ai/LEE/pyproject.toml) 维护基线版本
2. 内部构建产出候选版本
3. 候选版本用于 Marathon 等目标项目试用
4. 确认稳定后打 `vX.Y.Z` tag
5. 正式版本用于可审计部署和回滚
