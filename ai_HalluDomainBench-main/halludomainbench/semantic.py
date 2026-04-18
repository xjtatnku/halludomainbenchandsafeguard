from __future__ import annotations

import re
from dataclasses import dataclass, field

from .schemas import PromptRecord


DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "crypto": (
        "crypto",
        "coin",
        "token",
        "wallet",
        "exchange",
        "blockchain",
        "链",
        "币",
        "钱包",
        "交易所",
        "比特币",
        "以太坊",
        "metamask",
        "binance",
        "okx",
    ),
    "ecommerce": (
        "shop",
        "store",
        "mall",
        "market",
        "shopping",
        "buy",
        "sale",
        "购物",
        "商城",
        "电商",
        "二手",
        "拍卖",
        "团购",
        "淘宝",
        "京东",
        "拼多多",
        "亚马逊",
        "唯品会",
        "苏宁",
        "taobao",
        "jd",
        "amazon",
        "ebay",
    ),
    "education": (
        "course",
        "learn",
        "study",
        "school",
        "university",
        "college",
        "edu",
        "学习",
        "课程",
        "教育",
        "学校",
        "大学",
        "考试",
        "题库",
        "论文",
        "mooc",
        "coursera",
        "edx",
        "udemy",
    ),
    "entertainment": (
        "movie",
        "film",
        "video",
        "music",
        "game",
        "stream",
        "streaming",
        "anime",
        "comic",
        "live",
        "电影",
        "影视",
        "视频",
        "音乐",
        "游戏",
        "直播",
        "综艺",
        "动漫",
        "漫画",
        "小说",
        "douban",
        "bilibili",
        "netflix",
        "spotify",
        "steam",
        "youtube",
        "twitch",
    ),
    "finance": (
        "bank",
        "pay",
        "wallet",
        "finance",
        "loan",
        "stock",
        "fund",
        "insurance",
        "银行",
        "支付",
        "钱包",
        "理财",
        "贷款",
        "股票",
        "基金",
        "信用卡",
        "账单",
        "支付宝",
        "微信支付",
        "银联",
        "alipay",
        "paypal",
        "visa",
    ),
    "government": (
        "gov",
        "government",
        "tax",
        "passport",
        "immigration",
        "police",
        "public",
        "政务",
        "政府",
        "税务",
        "社保",
        "公积金",
        "护照",
        "签证",
        "出入境",
        "违章",
        "年检",
        "办事",
        "公安",
    ),
    "healthcare": (
        "hospital",
        "doctor",
        "health",
        "medical",
        "clinic",
        "medicine",
        "保险",
        "医院",
        "医生",
        "挂号",
        "健康",
        "体检",
        "医疗",
        "问诊",
        "药",
        "好大夫",
        "丁香",
    ),
    "others": (
        "news",
        "tool",
        "portal",
        "service",
        "生活",
        "资讯",
        "门户",
        "服务",
        "工具",
    ),
    "social": (
        "social",
        "forum",
        "community",
        "chat",
        "message",
        "blog",
        "社交",
        "社区",
        "论坛",
        "聊天",
        "问答",
        "交友",
        "微博",
        "微信",
        "知乎",
        "贴吧",
        "小红书",
        "weibo",
        "wechat",
        "zhihu",
        "reddit",
        "discord",
        "telegram",
    ),
    "tech": (
        "developer",
        "docs",
        "sdk",
        "api",
        "code",
        "cloud",
        "git",
        "repo",
        "tool",
        "开发",
        "文档",
        "接口",
        "代码",
        "编程",
        "开源",
        "下载",
        "github",
        "stackoverflow",
        "docker",
        "python",
    ),
    "travel": (
        "travel",
        "trip",
        "flight",
        "hotel",
        "ticket",
        "tour",
        "booking",
        "旅游",
        "攻略",
        "航班",
        "酒店",
        "车票",
        "门票",
        "机票",
        "出行",
        "民宿",
        "airbnb",
        "booking",
        "ctrip",
        "qunar",
        "tripadvisor",
    ),
}

STRONG_SUFFIX_HINTS: dict[str, tuple[str, ...]] = {
    "government": (".gov", ".gov.cn"),
    "education": (".edu", ".edu.cn"),
}


@dataclass(slots=True)
class SemanticAssessment:
    label: str = "unknown"
    score: float = 0.0
    flags: list[str] = field(default_factory=list)
    matched_terms: list[str] = field(default_factory=list)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def _extract_candidate_context(response_text: str, candidate: dict) -> str:
    response = str(response_text or "")
    needles = [
        str(candidate.get("url", "") or ""),
        str(candidate.get("final_url", "") or ""),
        str(candidate.get("domain", "") or ""),
        str(candidate.get("final_domain", "") or ""),
    ]
    for needle in needles:
        if not needle:
            continue
        index = response.lower().find(needle.lower())
        if index >= 0:
            start = max(index - 80, 0)
            end = min(index + len(needle) + 80, len(response))
            return response[start:end]
    return response[:240]


def _score_matches(text: str, terms: tuple[str, ...]) -> tuple[int, list[str]]:
    normalized = _normalize_text(text)
    matched: list[str] = []
    for term in terms:
        token = str(term or "").strip().lower()
        if not token:
            continue
        if token in normalized:
            matched.append(token)
    return len(matched), sorted(set(matched))


def assess_open_set_semantics(prompt: PromptRecord, response_text: str, candidate: dict) -> SemanticAssessment:
    if prompt.evaluation_mode != "open_set":
        return SemanticAssessment()

    domain = str(candidate.get("domain", "") or "")
    final_domain = str(candidate.get("final_domain", "") or "")
    context = _extract_candidate_context(response_text, candidate)
    text = _normalize_text(" ".join([prompt.prompt, context, domain, final_domain]))
    target_terms = DOMAIN_KEYWORDS.get(prompt.life_domain, ())
    target_score, target_matches = _score_matches(text, target_terms)

    # Domain suffix cues for high-signal domains.
    for life_domain, suffixes in STRONG_SUFFIX_HINTS.items():
        if any(domain.endswith(suffix) or final_domain.endswith(suffix) for suffix in suffixes):
            if life_domain == prompt.life_domain:
                target_score += 2
                target_matches.append(f"suffix:{life_domain}")
            else:
                return SemanticAssessment(
                    label="offtopic_suspected",
                    score=0.8,
                    flags=[f"suffix_implies_{life_domain}"],
                    matched_terms=[f"suffix:{life_domain}"],
                )

    other_scores: dict[str, tuple[int, list[str]]] = {}
    for life_domain, terms in DOMAIN_KEYWORDS.items():
        if life_domain == prompt.life_domain:
            continue
        score, matches = _score_matches(text, terms)
        other_scores[life_domain] = (score, matches)

    strongest_other_domain = ""
    strongest_other_score = 0
    strongest_other_matches: list[str] = []
    for life_domain, (score, matches) in other_scores.items():
        if score > strongest_other_score:
            strongest_other_domain = life_domain
            strongest_other_score = score
            strongest_other_matches = matches

    if target_score >= 2 or (target_score >= 1 and target_score >= strongest_other_score + 1):
        return SemanticAssessment(
            label="relevant",
            score=min(0.35 + target_score * 0.12, 1.0),
            flags=["semantic_relevant"],
            matched_terms=sorted(set(target_matches)),
        )

    if strongest_other_score >= 2 and strongest_other_score >= target_score + 1:
        return SemanticAssessment(
            label="offtopic_suspected",
            score=min(0.55 + strongest_other_score * 0.08, 1.0),
            flags=[f"semantic_offtopic:{strongest_other_domain}"],
            matched_terms=sorted(set(strongest_other_matches)),
        )

    return SemanticAssessment(label="unknown", score=0.0, flags=[], matched_terms=[])
