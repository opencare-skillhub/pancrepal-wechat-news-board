---
name: wechat-mp-monitor
description: 公众号更新监控与公众号文章清洗 skill，用于生成 Dashboard、维护去重状态，并清理导出内容以提升 RAG 质量。
triggers:
  - 公众号监控
  - 公众号更新
  - mp-monitor
  - 微信公众号监控
  - 清洗公众号文章
  - RAG 清洗
---

# WeChat MP Monitor

用于监控微信公众号更新，并配套清洗导出的文章内容。监控页面保留网页 Dashboard，同时额外生成适配公众号编辑器粘贴的 inline HTML 版；两者都使用 xyb 风格资源，顶部使用小胰宝 logo 头图，底部使用小胰宝公众号标准 footer。

## 组成

- `scripts/mp-monitor.py`：拉取公众号最新文章并生成 Dashboard
- `scripts/clean_rag_articles.py`：清洗导出的公众号文章，去掉广告、编辑信息、引导关注等无关内容
- `templates/mp-dashboard_xyb_style.html`：公众号监控页面的 xyb 风格模板骨架
- `templates/mp-article_inline.html`：公众号编辑器兼容的 inline 版模板骨架
- `xyb-wechat-article-generator/`：参考的 xyb 文章模板与样式资源，供监控页风格对齐
- `~/Downloads/wechat-monitor/state/mp-monitor.json`：已采集文章去重状态
- `~/Downloads/wechat-monitor/cache/mp-dashboard.html`：Dashboard 页面
- `~/Downloads/wechat-monitor/cache/mp-article.html`：公众号编辑器兼容的 inline HTML

## 常用命令

```bash
python3 wechat-mp-monitor/scripts/mp-monitor.py
python3 wechat-mp-monitor/scripts/mp-monitor.py --article
python3 wechat-mp-monitor/scripts/clean_rag_articles.py --report
```

## 当前监控公众号

- 恒瑞 On Call (`MzA4MDQ3NjM0MQ==`)
- 胰友会 (`Mzg4MTU4NDYxNA==`)
- Medicina麦迪希那 (`Mzg5ODg0MzUyMA==`)
- slope & share (`MzE5MTIxMDY5MQ==`)
- 劲方医药GenFleet (`MzU5NTQ1MDk2Mw==`)
- SXCHGCP
- GCP小行家
- 福肿24区
- 浙大二院临床药理中心
- 北京高博医院
- 西安交大二附院临床试验研究中心
- 天津市肿瘤医院临床试验中心
- 医周科技
- 鹤医声
- 长海医院胰腺肝胆外科
- 复旦大学附属华山医院胰腺外科
- 安医二附院肿瘤中心
- 中山胰腺肿瘤中心
- 四川省肿瘤医院临床研究部
- 浙江省肿瘤医院I期临床病房
- 张煜医生
- 丁香园肿瘤前沿
- 丁香园肿瘤时间
- FUSCC 胰腺肿瘤综合治疗部
- 小胰宝助手

## 指定根文件清洗

```bash
python3 wechat-mp-monitor/scripts/clean_rag_articles.py \
  --include-root-file RAS_不可能成药_的终局_Daraxonrasib改写胰腺癌治疗史.md \
  --include-root-file 2026_ASCO_胰腺癌研究全景报告.md
```

## 产物规则

- 清洗后的文件写入同级目录的 `_clean` 子目录
- 原始文件保持不变
- 清洗报告打印按目录统计

## 监控页面生成流程

1. `scripts/mp-monitor.py` 抓取公众号最新文章与统计数据
2. 用 `templates/mp-dashboard_xyb_style.html` 作为页面骨架
3. 注入账号卡片、文章链接、统计数字和时间戳
4. 顶部保留小胰宝 logo 与标题，结构要和 xyb 文章模板一致
5. 页脚固定为小胰宝标准 footer，不保留旧的 Hermes footer
6. 同时输出网页版 `mp-dashboard.html` 和公众号版 `mp-article.html`
