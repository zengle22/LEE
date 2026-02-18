---
description: Write engineering article with structured prompt - provide topic, viewpoint, scenario, and components
---

# LEE Article Write

Write an engineering article using structured prompt.

## Usage

When user wants to write an engineering article, invoke this command and provide:

- **Topic**: Article title
- **Core Viewpoint**: One-sentence core argument
- **Real Scenario**: A concrete engineering scenario or case
- **Core Components**: 3-4 core components (comma-separated)

## Writing Requirements

### Style
- Rational, restrained, calm
- No hype, no鸡汤 (chicken soup)
- No jargon dumping
- Engineering quality
- Short paragraphs (max 4 lines each)
- At least 3 "golden quotes" (two-line format)

### Structure (7 Steps)

1. **Pain Point (100-200 chars)**: Start with "你有没有遇到过……"
2. **Scenario还原**: Use CLI, logs, files, states
3. **Structural Explanation**: "问题不在模型能力。问题在结构。"
4. **Component Breakdown**: 3-4 components with examples
5. **Trend Judgment**: Calm analysis of trends
6. **Target Audience**: Engineers and entrepreneurs
7. **Closing Quote**: Two-line golden ending

### Rules
- Max 2500 words
- No "总结如下"
- No marketing tone
- No "震撼""颠覆"

## Example

Topic: 为什么 Spec 不能解决治理问题？
Core Viewpoint: Spec 是边界描述，不是执行约束。
Real Scenario: Agent 按 Spec 输出，但运行仍然出错。
Core Components: 输入契约、输出契约、运行验证、证据系统
