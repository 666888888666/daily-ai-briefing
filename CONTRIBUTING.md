# Contributing

感谢你帮助改善 Daily AI Briefing。优先欢迎四类贡献：新增稳定的一手来源、修复失效 Feed、改进解析兼容性、用可复现案例完善评分或核验规则。

新增来源时，请同时更新 `references/source-registry.yaml`；只有可公开访问、允许正常读取且结构稳定的 RSS、Atom 或 JSON Feed 才加入 `sources/feeds.json`。需要登录、绕过付费墙、使用私人 Cookie、违反站点规则或高度依赖页面结构的来源，不进入自动抓取配置，可以保留为 Skill 的实时搜索来源。

提交前请运行：

```bash
python scripts/validate_feed.py feed/latest.json
python -m py_compile scripts/build_feed.py scripts/validate_feed.py
```

公共 Feed 只保存候选信息，不应包含密钥、Cookie、私人联系方式或受版权保护的全文。新增解析器时请保留“单个来源失败不影响整体构建”的行为，并把失败写入 `source_health`。
