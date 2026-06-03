# wechat-mp-monitor

一个用于监控微信公众号更新、生成网页 Dashboard 和公众号可粘贴版 HTML 的本地 Skill 示例。

## 来源与说明

- 本项目基于开源项目 [wechat-article-exporter](https://github.com/wechat-article/wechat-article-exporter) 的思路和本地资源整理
- 文档参考 [MPText 文档](https://docs.mptext.top/)
- 参考了同目录下的 `xyb-wechat-article-generator` 公众号排版模板
- 页面样式采用 xyb 风格资源，公众号版输出采用 inline HTML 结构
- 感谢开发者的 ❤️ 开源

## 合规使用提醒

- 仅在你有权限的公众号数据和本地账号环境中使用
- 请遵守公众号平台、数据接口和内容抓取相关的服务条款
- 不要把真实 API Key、fakeid、账号配置直接提交到公开仓库
- 建议把敏感配置放在本地 `.env` 中，只提交 `.env.template`
- `.env.template` 已内置默认关键词，`.env` 只建议保留 `MP_API_KEY` 和你自己的账号映射

## 配置

复制模板：

```bash
cp .env.template .env
```

然后填写：

- `MP_API_KEY`：公众号接口 API Key
- `MP_ACCOUNTS_JSON`：公众号名称到 fakeid 的 JSON 映射
- `MP_SEARCH_KEYWORDS`：搜索/相关性关键词
- `MP_PRIORITY_KEYWORDS`：优先排序关键词
- `MP_PANCREATIC_PATTERNS`：胰腺相关硬过滤词
- `MP_TRIAL_PATTERNS`：临床试验优先词
- `MP_NEW_DRUG_PATTERNS`：新药和新方案优先词
- `MP_NEGATIVE_PATTERNS`：低价值内容过滤词

## 生成

```bash
python3 wechat-mp-monitor/scripts/mp-monitor.py
python3 wechat-mp-monitor/scripts/mp-monitor.py --article
python3 wechat-mp-monitor/scripts/mp-monitor.py --dashboard
```

输出目录：

- `~/Downloads/wechat-monitor/cache/mp-dashboard.html`
- `~/Downloads/wechat-monitor/cache/mp-article.html`
- `~/Downloads/wechat-monitor/state/mp-monitor.json`
