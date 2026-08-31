---
name: daily-ai-briefing
description: Generate a verified, product-focused Chinese Daily AI Briefing from the repository's public candidate feed, with live-source fallback when the feed is stale or incomplete. Use when the user asks for today's AI briefing, AI 日报, AI 资讯精选, or a product-oriented summary of recent AI developments.
---

# Daily AI Briefing

把分散的 AI 信息转化为一份经过筛选、核验并带有产品视角的中文日报。默认体验只有一句话：用户说“生成今天的 AI Briefing”，你直接生成，不做首次配置，不要求用户选择来源。

## 默认输入

1. 先读取仓库公共 Feed：`https://raw.githubusercontent.com/666888888666/daily-ai-briefing/main/feed/latest.json`。
2. Feed 的 `generated_at` 距当前时间不超过 30 小时且覆盖本期窗口时，以它作为候选池；不要把 Feed 中的候选直接视为已核验事实。
3. Feed 缺失、过期、来源抓取失败或候选明显不足时，使用联网搜索补齐。优先查 P0 官方来源，并在正文中给出可访问的 Primary Source 链接。
4. 若运行环境不能联网，明确写明 Feed 的生成时间及覆盖限制；不要伪装成实时日报。

## 运行参数

- 时区：Asia/Shanghai。
- 主窗口：前一日 14:00 至当日 14:00；14:30 后运行。
- 重大事件可回溯 48 小时，但已报道且没有新增信息的事件不得重复进入。
- 默认中文输出，面向 AI 产品经理、AI 创业者和 AI 从业者。
- 目标 6–10 条，允许少于 6 条，宁缺毋滥。

## 执行

先读取 [来源登记表](references/source-registry.yaml)、[评分规则](references/scoring-rubric.md)、[核验规则](references/verification-rules.md) 与 [编辑规则](references/editorial-rules.md)。需要生成长图或视觉版时再读取 [视觉规范](references/visual-report-spec.md)。

对候选依次完成时间过滤、事件归一化、去重聚类、历史事件检查、硬性排除、五维评分、事实核验、编辑排序、产品解释、行动分类和最终质检。严格区分事实与判断；同一事件有多个来源时，优先引用更高优先级的原始来源。

使用 [日报模板](templates/briefing.md) 输出。栏目不设配额，没有高质量内容时省略对应栏目。每条入选事件必须包含可信度标签、What happened、Why it matters、Primary Source；只有存在具体变化时才写 Product Lens；Action 只能是 TRY、TEST、READ、WATCH 或 NONE。

在后台按 [审计日志模板](templates/audit-log.json) 记录候选数量、拒绝原因、评分、核验等级和来源健康状况。除非用户要求，不在正式日报中展示审计日志。

## 不可违反的边界

- C｜Unverified 默认不得进入 Top Signals。
- 不把普通融资、普通合作、无产品意义的 Benchmark 微增、重复排行榜、单纯观点、无新增事实的采访、股价变化或 AI 概念营销塞进日报。
- 禁止“行业正在快速发展”“值得持续关注”“带来机会和挑战”等空洞句子；不能指出能力、工作流或竞争关系的具体变化时，删除该分析。
- 不编造来源、时间、评分、引用或历史状态。无法核验时降低等级或剔除。
