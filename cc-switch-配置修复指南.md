# Claude Official 正确配置

## 官方登录配置（不需要 base_url）

如果您想使用 Anthropic 官方 API：

1. 在 CC Switch 中点击"添加供应商"
2. 选择 **"官方登录"** 预设
3. **不要填写** base_url 字段（留空）
4. 填写您的 Anthropic API Key
5. 保存并启用

然后重启 Claude Code，按照官方流程登录即可。

---

## 中转服务配置（需要 base_url）

如果您使用中转服务，必须填写正确的 base_url：

### PackyCode
- **Base URL**: `https://api.packyapi.com/v1`
- **API Key**: 从 PackyCode 获取
- **模型**: `claude-sonnet-4-20250514` 或其他

### 智谱 GLM (Claude 兼容)
- **Base URL**: `https://open.bigmodel.cn/api/paas/v4`
- **API Key**: 从智谱获取
- **模型**: `claude-3.5-sonnet` 或其他

### AIGoCode
- **Base URL**: 询问服务商获取
- **API Key**: 从 AIGoCode 获取

### DMXAPI
- **Base URL**: 询问服务商获取
- **API Key**: 从 DMXAPI 获取

---

## 如何获取正确的 Base URL

1. **查看服务商文档**：每个中转服务都会提供 API 文档
2. **联系客服**：直接询问服务商的 base_url
3. **查看 API 端点**：通常是类似 `https://api.example.com/v1` 的格式

---

## 快速修复步骤

### 如果您有官方 API Key：
1. 删除当前的错误配置
2. 重新添加"官方登录"预设
3. 留空 base_url
4. 填写官方 API Key

### 如果您使用中转服务：
1. 联系服务商确认 base_url
2. 在 CC Switch 中编辑供应商配置
3. 填写正确的 base_url
4. 保存并重新启用
