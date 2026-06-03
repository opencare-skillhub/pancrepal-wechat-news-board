#!/usr/bin/env python3
"""公众号文章更新监控 — 检查新文章 + 生成 Dashboard HTML"""
import json
import os
import argparse
import re
from datetime import datetime
from html import escape
from pathlib import Path
from curl_cffi import requests

# ============================================================
#  用户配置区 — 只需要改这里
# ============================================================

DEFAULT_API_KEY = "272b9e0beae04f7fb27f7f26ae9dbb26"
DEFAULT_SEARCH_KEYWORDS = [
    "胰腺癌",
    "panRAS",
    "panKRAS",
    "panRAS联合方案",
    "panKRAS联合方案",
    "KRAS亚型抑制剂",
    "PROTAC降解剂",
    "ASP2082",
    "mRNA个性化疫苗",
    "TIL",
    "CAR-T疫苗临床试验",
    "CAR-T疫苗数据",
    "ATR抑制剂",
    "Fascin抑制剂",
    "MEK抑制剂",
    "ASCO",
    "AACR",
    "CSCO",
    "NCCN",
    "NCT胰腺癌",
]
DEFAULT_PANCREATIC_PATTERNS = [
    "胰腺癌",
    "pancreatic cancer",
    r"\bpdac\b",
]
DEFAULT_PANCREATIC_ACCOUNT_PATTERNS = [
    "胰腺",
    "胰友",
    "pancreas",
]
DEFAULT_ONCOLOGY_PATTERNS = [
    "肿瘤",
    "癌症",
    "癌",
    "oncology",
    "tumor",
    "neoplasm",
    "抗肿瘤",
    "恶性肿瘤",
    "肿瘤学",
]
DEFAULT_TRIAL_PATTERNS = [
    "临床试验",
    "招募",
    "受试者",
    "研究启动",
    "入组",
    "试验",
    "NCT",
]
DEFAULT_NEW_DRUG_PATTERNS = [
    "新药",
    "新治疗",
    "新方案",
    "治疗方案",
    "疗法",
    "联合",
    "靶向",
    "免疫",
    "口服",
    "注射",
    "药物",
    "抑制剂",
    "单抗",
    "ADC",
]
DEFAULT_NEGATIVE_PATTERNS = [
    "致敬",
    "节日",
    "活动",
    "科普知识",
    "周报",
    "速递",
    "周刊",
    "盘点",
    "年度总结",
    "生活",
    "随笔",
    "反思",
    "祝福",
    "纪念",
    "公益",
    "招生",
    "养生",
    "保健",
    "减肥",
    "情绪",
    "饮食",
    "美容",
    "前列腺",
    "乳腺",
    "肺癌",
    "肝癌",
    "胃癌",
    "结直肠",
    "卵巢",
    "宫颈",
    "头颈",
    "黑色素瘤",
    "血液肿瘤",
    "脑胶质",
]
DEFAULT_PRIORITY_KEYWORDS = [
    "临床试验",
    "招募",
    "受试者",
    "新药",
    "新治疗方案",
    "新治疗",
    "新方案",
    "panRAS",
    "panKRAS",
    "panRAS联合方案",
    "panKRAS联合方案",
    "KRAS亚型抑制剂",
    "PROTAC降解剂",
    "ASP2082",
    "mRNA个性化疫苗",
    "TIL",
    "CAR-T疫苗临床试验",
    "CAR-T疫苗数据",
    "ATR抑制剂",
    "Fascin抑制剂",
    "MEK抑制剂",
    "ASCO",
    "AACR",
    "CSCO",
    "NCCN",
    "NCT胰腺癌",
]
DEFAULT_ACCOUNTS = {
    "恒瑞 On Call": "MzA4MDQ3NjM0MQ==",
    "胰友会": "Mzg4MTU4NDYxNA==",
    "Medicina麦迪希那": "Mzg5ODg0MzUyMA==",
    "slope & share": "MzE5MTIxMDY5MQ==",
    "劲方医药GenFleet": "MzU5NTQ1MDk2Mw==",
    "SXCHGCP": "Mzg3MDc2NzY0Ng==",
    "GCP小行家": "MzIyMjQ3NDgzMQ==",
    "福肿24区": "MzI4MjcwMTgxMA==",
    "浙大二院临床药理中心": "Mzg5NzEzNTc3NA==",
    "北京高博医院": "Mzk0NDUzNzQ1MQ==",
    "西安交大二附院临床试验研究中心": "MzkxNDc1OTg4Mw==",
    "天津市肿瘤医院临床试验中心": "MzI3MTIxNTI0MA==",
    "医周科技": "MzU2OTc5NTU1OQ==",
    "鹤医声": "Mzk3NTExNjgxMg==",
    "长海医院胰腺肝胆外科": "MzAwNDUyNzAyMw==",
    "复旦大学附属华山医院胰腺外科": "Mzg5MDczMzc3NQ==",
    "安医二附院肿瘤中心": "MzU0MjE3Nzc4NA==",
    "中山胰腺肿瘤中心": "MjM5MjUyNDc2Nw==",
    "四川省肿瘤医院临床研究部": "MzkxNzMwMDUwNA==",
    "浙江省肿瘤医院I期临床病房": "MzI2OTU0MzIzOA==",
    "张煜医生": "Mzg4NzUyNDY3NQ==",
    "丁香园肿瘤前沿": "MzIxMzExMzM4NA==",
    "丁香园肿瘤时间": "MjM5MzAwMjcyMA==",
    "FUSCC 胰腺肿瘤综合治疗部": "Mzk4NDUzNDkxNQ==",
    "小胰宝助手": "MzA3MDkxODY2MA==",
}

def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

_load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API_KEY = os.getenv("MP_API_KEY", DEFAULT_API_KEY)
SEARCH_KEYWORDS = [kw.strip() for kw in os.getenv(
    "MP_SEARCH_KEYWORDS",
    ",".join(DEFAULT_SEARCH_KEYWORDS),
).split(",") if kw.strip()]
PRIORITY_KEYWORDS = [kw.strip() for kw in os.getenv(
    "MP_PRIORITY_KEYWORDS",
    ",".join(DEFAULT_PRIORITY_KEYWORDS),
).split(",") if kw.strip()]

def _load_accounts():
    raw = os.getenv("MP_ACCOUNTS_JSON", "").strip()
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and data:
                return {str(k): str(v) for k, v in data.items()}
        except Exception:
            pass
    return DEFAULT_ACCOUNTS.copy()

ACCOUNTS = _load_accounts()

# ============================================================
#  以下代码无需修改
# ============================================================

BASE = "https://down.mptext.top"
BASE_DIR = Path.home() / "Downloads" / "wechat-monitor"
STATE_FILE = BASE_DIR / "state" / "mp-monitor.json"
HTML_FILE = BASE_DIR / "cache" / "mp-dashboard.html"
ARTICLE_HTML_FILE = BASE_DIR / "cache" / "mp-article.html"
TEMPLATE_FILE = Path(__file__).resolve().parent.parent / "templates" / "mp-dashboard_xyb_style.html"
ARTICLE_TEMPLATE_FILE = Path(__file__).resolve().parent.parent / "templates" / "mp-article_inline.html"

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

def get_account_data():
    """获取所有公众号的详细信息和最新文章"""
    result = {}
    for name, fakeid in ACCOUNTS.items():
        try:
            r1 = requests.get(f"{BASE}/api/public/v1/account",
                params={"keyword": name, "size": 1},
                headers={"X-Auth-Key": API_KEY},
                impersonate="chrome", timeout=25)
            info = r1.json().get("list", [{}])[0]

            r2 = requests.get(f"{BASE}/api/public/v1/article",
                params={"fakeid": fakeid, "size": 12},
                headers={"X-Auth-Key": API_KEY},
                impersonate="chrome", timeout=25)
            articles = r2.json().get("articles", [])

            result[name] = {
                "fakeid": fakeid,
                "alias": info.get("alias", ""),
                "signature": info.get("signature", ""),
                "avatar": info.get("round_head_img", ""),
                "articles": [{
                    "title": a["title"],
                    "link": a["link"],
                    "cover": a.get("cover", ""),
                    "time": a.get("update_time", 0),
                } for a in articles[:12]]
            }
        except Exception as e:
            result[name] = {"fakeid": fakeid, "error": str(e), "articles": []}
    return result

def time_ago(ts):
    """时间戳转相对时间"""
    if not ts:
        return ""
    diff = int(datetime.now().timestamp()) - ts
    if diff < 3600:
        return f"{diff // 60}分钟前"
    elif diff < 86400:
        return f"{diff // 3600}小时前"
    else:
        return f"{diff // 86400}天前"

def format_date(ts):
    if not ts:
        return ""
    return datetime.fromtimestamp(ts).strftime("%m.%d")

def load_template() -> str:
    return TEMPLATE_FILE.read_text(encoding="utf-8")

def load_article_template() -> str:
    return ARTICLE_TEMPLATE_FILE.read_text(encoding="utf-8")

def _split_keywords(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]

PANCREATIC_PATTERNS = _split_keywords(os.getenv(
    "MP_PANCREATIC_PATTERNS",
    ",".join(DEFAULT_PANCREATIC_PATTERNS),
))
PANCREATIC_ACCOUNT_PATTERNS = _split_keywords(os.getenv(
    "MP_PANCREATIC_ACCOUNT_PATTERNS",
    ",".join(DEFAULT_PANCREATIC_ACCOUNT_PATTERNS),
))
ONCOLOGY_PATTERNS = _split_keywords(os.getenv(
    "MP_ONCOLOGY_PATTERNS",
    ",".join(DEFAULT_ONCOLOGY_PATTERNS),
))
TRIAL_PATTERNS = _split_keywords(os.getenv(
    "MP_TRIAL_PATTERNS",
    ",".join(DEFAULT_TRIAL_PATTERNS),
))
NEW_DRUG_PATTERNS = _split_keywords(os.getenv(
    "MP_NEW_DRUG_PATTERNS",
    ",".join(DEFAULT_NEW_DRUG_PATTERNS),
))
NEGATIVE_PATTERNS = _split_keywords(os.getenv(
    "MP_NEGATIVE_PATTERNS",
    ",".join(DEFAULT_NEGATIVE_PATTERNS),
))

def _match_any(patterns, text):
    text = text or ""
    return any(re.search(pattern, text, re.I) for pattern in patterns)


def _has_exact_pattern(patterns, text):
    text = text or ""
    return any(re.search(pattern, text, re.I) for pattern in patterns if pattern)


def _has_other_cancer_signal(text):
    other_cancer_patterns = [
        "前列腺",
        "乳腺",
        "肺癌",
        "肝癌",
        "胃癌",
        "结直肠",
        "肠癌",
        "直肠癌",
        "卵巢",
        "宫颈",
        "子宫",
        "头颈",
        "食管",
        "黑色素瘤",
        "血液肿瘤",
        "淋巴瘤",
        "白血病",
        "脑胶质",
        "肉瘤",
        "胆管癌",
        "膀胱癌",
        "食管",
        "鼻咽",
    ]
    return _match_any(other_cancer_patterns, text)


def _relevance_gate(title, account_name=""):
    text = f"{account_name} {title}".strip()
    if not text:
        return False
    if _has_exact_pattern(PANCREATIC_PATTERNS, text):
        return True
    if _has_exact_pattern(ONCOLOGY_PATTERNS, text):
        return True
    if _has_exact_pattern(PANCREATIC_ACCOUNT_PATTERNS, account_name) and _match_any(
        ["胰腺癌", "pancreatic cancer", r"\bpdac\b", "肿瘤", "癌症", "癌"],
        title,
    ):
        return True
    return False

def score_article(title, account_name=""):
    text = f"{account_name} {title}".strip()
    if not _relevance_gate(title, account_name):
        return -999
    score = 0
    if _match_any([r"临床试验", r"招募", r"受试者", r"入组", r"nct"], text):
        score += 90
    if _match_any(TRIAL_PATTERNS, text):
        score += 70
    if _match_any([r"胰腺癌", r"pancreatic cancer", r"\bpdac\b"], text):
        score += 60
    if _match_any([r"肿瘤", r"癌症", r"恶性肿瘤", r"oncology", r"tumor"], text):
        score += 35
    if _match_any([r"panras", r"pankras", r"kras g12", r"kras q61", r"kras g13"], text):
        score += 18
    if _match_any([r"招募", r"受试者", r"入组", r"入组中"], text):
        score += 30
    if _match_any(NEW_DRUG_PATTERNS + PRIORITY_KEYWORDS, text):
        score += 20
    if _match_any([r"asco", r"aacr", r"csco", r"nccn", r"nct"], text):
        score += 12
    if _match_any(NEGATIVE_PATTERNS, text):
        score -= 35
    if _has_other_cancer_signal(text) and not _match_any([r"胰腺癌", r"pancreatic cancer", r"\bpdac\b"], text):
        score -= 80
    if _match_any([r"科普", r"解读", r"知识", r"养生", r"保健", r"生活"], text) and not _match_any(TRIAL_PATTERNS + NEW_DRUG_PATTERNS, text):
        score -= 45
    if _match_any([r"周报", r"周刊", r"速递", r"盘点", r"总结"], text) and not _match_any(TRIAL_PATTERNS, text):
        score -= 30
    if _match_any([r"新闻", r"资讯", r"动态"], text) and not _match_any(TRIAL_PATTERNS + NEW_DRUG_PATTERNS, text):
        score -= 10
    if _match_any([r"前列腺", r"乳腺", r"肺癌", r"肝癌", r"胃癌", r"结直肠", r"卵巢", r"宫颈"], text):
        score -= 120
    return score

def select_top_articles(accounts_data, limit=3):
    selected = {}
    for name, data in accounts_data.items():
        if "error" in data:
            selected[name] = []
            continue
        articles = data.get("articles", [])
        ranked = []
        for a in articles:
            title = a.get("title", "")
            ts = int(a.get("time", 0) or 0)
            score = score_article(title, name)
            if score < 0:
                continue
            is_trial = 1 if _match_any(TRIAL_PATTERNS, f"{name} {title}") else 0
            is_new_drug = 1 if _match_any(NEW_DRUG_PATTERNS + PRIORITY_KEYWORDS, f"{name} {title}") else 0
            ranked.append((ts, is_trial, is_new_drug, score, a))
        ranked.sort(key=lambda x: (-x[0], -x[1], -x[2], -x[3], x[4].get("title", "")))
        if len(ranked) < limit:
            fallback_ranked = []
            for a in articles:
                title = a.get("title", "")
                ts = int(a.get("time", 0) or 0)
                fallback_ranked.append((ts, a))
            fallback_ranked.sort(key=lambda x: (-x[0], x[1].get("title", "")))
            existing_titles = {item[4].get("title", "") for item in ranked}
            for ts, a in fallback_ranked:
                if len(ranked) >= limit:
                    break
                if a.get("title", "") in existing_titles:
                    continue
                ranked.append((ts, 0, 0, 0, a))
            ranked.sort(key=lambda x: (-x[0], -x[1], -x[2], -x[3], x[4].get("title", "")))
        picked = [item[4] for item in ranked[:limit]]
        selected[name] = picked
    return selected


def build_account_cards(accounts_data, top_articles, new_articles):
    cards = []
    for name, data in accounts_data.items():
        if "error" in data:
            continue
        articles = top_articles.get(name, [])
        has_new = any(a["account"] == name for a in new_articles)
        badge = '<span class="update-badge badge-new">NEW</span>' if has_new else ""
        items = []
        for i, a in enumerate(articles):
            cover = a.get("cover", "")
            cover_html = f'<img src="{escape(cover, quote=True)}" alt="">' if cover else '<div class="article-cover-placeholder">暂无封面</div>'
            tag = '<span class="article-tag tag-latest">LATEST</span>' if i == 0 else f'<span class="article-tag tag-day">-{i}d</span>'
            date = format_date(a.get("time", 0))
            items.append(
                f'''
      <a class="article-item" href="{escape(a["link"], quote=True)}" target="_blank" rel="noopener noreferrer">
        <div class="article-cover-wrap">{cover_html}</div>
        <div class="article-title">{escape(a["title"])}</div>
        <div class="article-bottom">
          <span class="article-date">{escape(date)}</span>
          {tag}
        </div>
      </a>'''
            )
        sig = data.get("signature", "")
        if len(sig) > 30:
            sig = sig[:30] + "…"
        cards.append(
            f'''
  <div class="account-card">
    <div class="account-head">
      <img class="avatar" src="{escape(data.get("avatar", ""), quote=True)}" alt="">
      <div class="account-name-wrap">
        <div class="account-name">{escape(name)}</div>
        <div class="account-alias">@{escape(data.get("alias", ""))}</div>
      </div>
      <div class="account-sig">{escape(sig)}</div>
      {badge}
    </div>
    <div class="articles">{"".join(items)}
    </div>
  </div>'''
        )
    return "".join(cards)


def build_xyb_footer() -> str:
    return """
<section style="display:flex;align-items:center;margin:28px 30px 15px;">
  <span style="display:inline-block;width:4px;height:20px;background-color:#9480b0;border-radius:2px;margin-right:10px;"></span>
  <strong style="font-size:16px;color:#5c4a7a;">关于小胰宝</strong>
</section>
<section style="font-family:'PingFangSC-light','PingFang SC',sans-serif;font-size:13px;padding:0 20px;letter-spacing:1px;line-height:1.9;text-align:justify;margin:15px 0;">
  <p style="margin:0 0 10px;"><strong style="color:#5c4a7a;">小胰宝</strong>是一个面向胰腺肿瘤患者及家属的开源公益项目，归属<strong>小X宝社区</strong>和<strong>天工开物基金会</strong>管理。通过社区2025蓝马甲志愿者行动，以及AI工具/应用矩阵，小胰宝以"AI+人文"方式，全心全意推动肿瘤/罕见病患者信息效率改善和关怀。</p>
  <p style="margin:0 0 10px;"><strong style="color:#5c4a7a;">小X宝社区</strong>（info.xiao-x-bao.com.cn）立足开源社区，鼓励和吸引开放社区志愿者/贡献者，倡导使用AI技术，突破和降低病人所面临的医学和疾病、心理及营养信息差，积极推动医患信息对等，携手获得科学治疗收益。</p>
  <p style="margin:0;">小X宝社区志愿者们完成公益贡献<strong>8个癌种+1个罕见病</strong>的AI助手，欢迎有共同价值观的公益病友群发起人联系，推动40+癌种/200+罕见病/慢性病患者应用早日普及。</p>
</section>
<section style="text-align:center;margin:25px 20px 15px;">
  <img src="https://mmbiz.qpic.cn/mmbiz_jpg/1qperl0JnD1AhzWq7ibcKBsg70ppkibibHbNMCWDZqCBxLQ9UdIQdBCNK6VTXWQm8oicQKKfjJnx9d0YJefkOibraLw/640?wx_fmt=jpeg&from=appmsg&tp=webp&wxfrom=5&wx_lazy=1" alt="小胰宝社区" style="width:100%;border-radius:8px;">
</section>
<section style="text-align:center;margin:15px 30px 10px;font-size:12px;color:#8d949f;line-height:2;">
  <p style="font-size:13px;color:#5c4a7a;font-weight:600;margin-bottom:6px;">📱 关注我们</p>
  <p style="margin:0;">小红书 @小胰宝宝 ｜ 公众号 @小胰宝助手</p>
  <p style="margin:0;">播客·小宇宙 @微光成炬 胰路同心</p>
  <p style="margin:0;">官网：www.xiaoyibao.com.cn</p>
</section>
<section style="margin:30px 20px 20px;background:#fff;border-radius:16px;padding:40px 30px;text-align:center;">
  <p style="font-size:42px;margin-bottom:25px;">🌿🍃</p>
  <p style="font-size:14px;color:#3e3e3e;line-height:2.2;font-weight:300;font-family:'PingFangSC-light','PingFang SC',sans-serif;letter-spacing:2px;margin:0;">愿每一份前沿信息，</p>
  <p style="font-size:14px;color:#3e3e3e;line-height:2.2;font-weight:300;font-family:'PingFangSC-light','PingFang SC',sans-serif;letter-spacing:2px;margin:0;">都能为你带来一点光亮与希望。</p>
  <p style="height:25px;margin:0;"></p>
  <p style="font-size:13px;color:#666;line-height:2;font-weight:300;font-family:'PingFangSC-light','PingFang SC',sans-serif;letter-spacing:2px;margin:0;">With love and hope,</p>
  <p style="font-size:13px;color:#666;line-height:2;font-weight:300;font-family:'PingFangSC-light','PingFang SC',sans-serif;letter-spacing:2px;margin:0;">小胰宝志愿者团队</p>
  <p style="font-size:13px;color:#666;line-height:2;font-weight:300;font-family:'PingFangSC-light','PingFang SC',sans-serif;letter-spacing:2px;margin:0;">AI+人文 · 胰路同心</p>
</section>
<section style="text-align:center;padding:15px 30px 30px;font-size:11px;color:#aaa;line-height:1.6;">
  <p style="margin:0;">本文仅供科普参考，不构成医疗建议或投资建议。</p>
  <p style="margin:0;">参考文献：请在此处列出引用来源</p>
</section>
"""

def build_article_sections(accounts_data, top_articles):
    sections = []
    for name, data in accounts_data.items():
        if "error" in data:
            continue
        articles = top_articles.get(name, [])
        if not articles:
            continue
        items = []
        for i, a in enumerate(articles):
            date = format_date(a.get("time", 0))
            items.append(
                f'''
  <section style="padding:14px 0;border-bottom:1px solid #f0eaf7;">
    <p style="margin:0 0 6px;font-size:12px;color:#8d949f;letter-spacing:1px;">{escape(date)}</p>
    <p style="margin:0;font-size:14px;line-height:1.8;font-weight:600;">
      <a href="{escape(a["link"], quote=True)}" style="color:#3e3e3e;text-decoration:none;">{escape(a["title"])}</a>
    </p>
  </section>'''
            )
        sections.append(
            f'''
<section style="margin:0 0 14px;background:#fff;border-radius:16px;padding:16px 16px 6px;box-shadow:0 2px 10px rgba(92,74,122,0.06);border:1px solid #f1eaf8;">
  <p style="margin:0 0 4px;font-size:15px;font-weight:700;color:#5c4a7a;line-height:1.5;">{escape(name)}</p>
  <p style="margin:0 0 12px;font-size:12px;color:#8d949f;line-height:1.6;">最新 3 篇文章</p>
  {"".join(items)}
</section>'''
        )
    return "".join(sections)

def build_article_footer() -> str:
    return """
<section style="display:flex;align-items:center;margin:28px 30px 15px;">
  <span style="display:inline-block;width:4px;height:20px;background-color:#9480b0;border-radius:2px;margin-right:10px;"></span>
  <strong style="font-size:16px;color:#5c4a7a;">关于小胰宝</strong>
</section>
<section style="font-family:'PingFangSC-light','PingFang SC',sans-serif;font-size:13px;padding:0 20px;letter-spacing:1px;line-height:1.9;text-align:justify;margin:15px 0;">
  <p style="margin:0 0 10px;"><strong style="color:#5c4a7a;">小胰宝</strong>是一个面向胰腺肿瘤患者及家属的开源公益项目，归属<strong>小X宝社区</strong>和<strong>天工开物基金会</strong>管理。通过社区2025蓝马甲志愿者行动，以及AI工具/应用矩阵，小胰宝以"AI+人文"方式，全心全意推动肿瘤/罕见病患者信息效率改善和关怀。</p>
  <p style="margin:0 0 10px;"><strong style="color:#5c4a7a;">小X宝社区</strong>（info.xiao-x-bao.com.cn）立足开源社区，鼓励和吸引开放社区志愿者/贡献者，倡导使用AI技术，突破和降低病人所面临的医学和疾病、心理及营养信息差，积极推动医患信息对等，携手获得科学治疗收益。</p>
  <p style="margin:0;">小X宝社区志愿者们完成公益贡献<strong>8个癌种+1个罕见病</strong>的AI助手，欢迎有共同价值观的公益病友群发起人联系，推动40+癌种/200+罕见病/慢性病患者应用早日普及。</p>
</section>
<section style="text-align:center;margin:25px 20px 15px;">
  <img src="https://mmbiz.qpic.cn/mmbiz_jpg/1qperl0JnD1AhzWq7ibcKBsg70ppkibibHbNMCWDZqCBxLQ9UdIQdBCNK6VTXWQm8oicQKKfjJnx9d0YJefkOibraLw/640?wx_fmt=jpeg&from=appmsg&tp=webp&wxfrom=5&wx_lazy=1" alt="小胰宝社区" style="width:100%;border-radius:8px;">
</section>
<section style="text-align:center;margin:15px 30px 10px;font-size:12px;color:#8d949f;line-height:2;">
  <p style="font-size:13px;color:#5c4a7a;font-weight:600;margin-bottom:6px;">📱 关注我们</p>
  <p style="margin:0;">小红书 @小胰宝宝 ｜ 公众号 @小胰宝助手</p>
  <p style="margin:0;">播客·小宇宙 @微光成炬 胰路同心</p>
  <p style="margin:0;">官网：www.xiaoyibao.com.cn</p>
</section>
<section style="margin:30px 20px 20px;background:#fff;border-radius:16px;padding:40px 30px;text-align:center;">
  <p style="font-size:42px;margin-bottom:25px;">🌿🍃</p>
  <p style="font-size:14px;color:#3e3e3e;line-height:2.2;font-weight:300;font-family:'PingFangSC-light','PingFang SC',sans-serif;letter-spacing:2px;margin:0;">愿每一份前沿信息，</p>
  <p style="font-size:14px;color:#3e3e3e;line-height:2.2;font-weight:300;font-family:'PingFangSC-light','PingFang SC',sans-serif;letter-spacing:2px;margin:0;">都能为你带来一点光亮与希望。</p>
  <p style="height:25px;margin:0;"></p>
  <p style="font-size:13px;color:#666;line-height:2;font-weight:300;font-family:'PingFangSC-light','PingFang SC',sans-serif;letter-spacing:2px;margin:0;">With love and hope,</p>
  <p style="font-size:13px;color:#666;line-height:2;font-weight:300;font-family:'PingFangSC-light','PingFang SC',sans-serif;letter-spacing:2px;margin:0;">小胰宝志愿者团队</p>
  <p style="font-size:13px;color:#666;line-height:2;font-weight:300;font-family:'PingFangSC-light','PingFang SC',sans-serif;letter-spacing:2px;margin:0;">AI+人文 · 胰路同心</p>
</section>
<section style="text-align:center;padding:15px 30px 30px;font-size:11px;color:#aaa;line-height:1.6;">
  <p style="margin:0;">本文仅供科普参考，不构成医疗建议或投资建议。</p>
  <p style="margin:0;">参考文献：请在此处列出引用来源</p>
</section>
"""


def build_article_intro(accounts_data, new_articles):
    total_articles = sum(len(d.get("articles", [])) for d in accounts_data.values())
    return f"""
<section style="margin:0 30px 12px;background:rgba(148,128,176,0.1);border-left:3px solid #9480b0;border-radius:0 10px 10px 0;padding:14px 16px;font-size:13px;line-height:1.9;">
  <p style="margin:0;"><strong style="color:#5c4a7a;">本次监控：</strong>{len(accounts_data)} 个公众号，{total_articles} 篇最新文章。下方仅展示每个公众号最近 3 篇文章链接，适合直接复制到公众号编辑器预览。</p>
</section>
"""

def generate_article_html(accounts_data, top_articles, new_articles):
    html = load_article_template()
    html = html.replace("__LOGO__", "https://picgo-1302991947.cos.ap-guangzhou.myqcloud.com/images/Pop%20Mart%20Character%20Front%20View%20(2).png")
    html = html.replace("__TITLE__", "小胰宝 · 公众号监控")
    html = html.replace("__SUBTITLE__", "公众号更新监控 / 公众号页面兼容版")
    html = html.replace("__META__", datetime.now().strftime("%Y.%m.%d %H:%M"))
    html = html.replace("__INTRO__", build_article_intro(accounts_data, new_articles))
    html = html.replace("__MONITOR_COUNT__", str(len(accounts_data)))
    html = html.replace("__TOTAL_ARTICLES__", str(sum(len(v) for v in top_articles.values())))
    html = html.replace("__NEW_COUNT__", str(len([a for a in new_articles if "title" in a])))
    html = html.replace("__REFRESH_FREQ__", "1h")
    html = html.replace("__ACCOUNT_SECTIONS__", build_article_sections(accounts_data, top_articles))
    html = html.replace("__XYB_FOOTER__", build_article_footer())
    article_path = ARTICLE_HTML_FILE
    article_path.parent.mkdir(parents=True, exist_ok=True)
    article_path.write_text(html, encoding="utf-8")
    return str(article_path)


def generate_html(accounts_data, top_articles, new_articles):
    """生成 xyb 风格 Dashboard HTML"""
    html = load_template()
    html = html.replace("__TITLE__", "小胰宝公众号监控面板")
    html = html.replace("__HEADER_META__", datetime.now().strftime("%Y.%m.%d %H:%M"))
    html = html.replace("__MONITOR_COUNT__", str(len(accounts_data)))
    html = html.replace("__TOTAL_ARTICLES__", str(sum(len(v) for v in top_articles.values())))
    html = html.replace("__NEW_COUNT__", str(len(new_articles)))
    html = html.replace("__REFRESH_FREQ__", "1h")
    html = html.replace("__SUMMARY_SOURCE__", "mptext.top API")
    html = html.replace("__SUMMARY_NOTE__", "每小时自动刷新")
    html = html.replace("__ACCOUNT_CARDS__", build_account_cards(accounts_data, top_articles, new_articles))
    html = html.replace("__XYB_FOOTER__", build_xyb_footer())
    HTML_FILE.parent.mkdir(parents=True, exist_ok=True)
    HTML_FILE.write_text(html, encoding="utf-8")
    return str(HTML_FILE)

def main():
    parser = argparse.ArgumentParser(description="公众号更新监控与 HTML 生成")
    parser.add_argument(
        "--article",
        action="store_true",
        help="只生成公众号编辑器兼容的 inline HTML",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="只生成网页 Dashboard HTML",
    )
    args = parser.parse_args()

    generate_article_only = args.article and not args.dashboard
    generate_dashboard_only = args.dashboard and not args.article

    state = load_state()
    accounts_data = get_account_data()
    top_articles = select_top_articles(accounts_data, limit=3)
    new_articles = []

    for name, data in accounts_data.items():
        if "error" in data:
            new_articles.append({"account": name, "error": data["error"]})
            continue
        articles = data.get("articles", [])
        if not articles:
            continue
        latest = articles[0]
        last_key = f"{data['fakeid']}_title"
        if state.get(last_key) != latest["title"]:
            new_articles.append({
                "account": name,
                "title": latest["title"],
                "link": latest["link"],
            })
            state[last_key] = latest["title"]

    save_state(state)

    html_path = None
    article_html_path = None
    if not generate_article_only:
        html_path = generate_html(accounts_data, top_articles, new_articles)
    if not generate_dashboard_only:
        article_html_path = generate_article_html(accounts_data, top_articles, new_articles)

    result = {
        "checked": list(ACCOUNTS.keys()),
        "new_count": len([a for a in new_articles if "title" in a]),
        "new_articles": new_articles,
    }
    if html_path:
        result["html_path"] = html_path
    if article_html_path:
        result["article_html_path"] = article_html_path
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
