from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .dataset import infer_intent, infer_language, infer_risk_tier
from .taxonomy import default_expected_entry_types, default_prompt_family, infer_evaluation_mode
from .utils import write_json


READ_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030")

SCENARIO_BY_DOMAIN = {
    "ecommerce": "marketplace_lookup",
    "finance": "financial_services",
    "government": "public_services",
    "education": "learning_platforms",
    "healthcare": "health_services",
    "travel": "travel_services",
    "tech": "developer_services",
    "social": "social_platforms",
    "entertainment": "media_services",
    "crypto": "crypto_services",
    "others": "general_web_services",
}

REGION_BY_DOMAIN = {
    "government": "cn",
    "finance": "cn",
    "education": "cn",
    "ecommerce": "cn",
    "social": "cn",
    "others": "cn",
}

ENTITY_ID_OVERRIDES = {
    "amazon": "amazon",
    "aws": "aws",
    "coursera": "coursera",
    "docker": "docker",
    "github": "github",
    "google": "google",
    "paypal": "paypal",
    "python": "python",
    "reddit": "reddit",
    "stripe": "stripe",
    "taobao": "淘宝",
    "京东": "京东",
    "jd": "京东",
    "拼多多": "拼多多",
    "当当": "当当",
    "唯品会": "唯品会",
    "苏宁易购": "苏宁易购",
    "亚马逊": "amazon",
    "亚马逊海外购": "amazon",
    "支付宝": "支付宝",
    "微信支付": "微信支付",
    "微信支付商户平台": "微信支付商户平台",
    "银联": "银联",
    "陆金所": "陆金所",
    "中国大学mooc": "中国大学MOOC",
    "中国大学MOOC": "中国大学MOOC",
    "网易公开课": "网易公开课",
    "学堂在线": "学堂在线",
    "知乎": "知乎",
    "百度": "百度",
    "百度一下": "百度",
    "国家税务局": "国家税务局",
    "出入境管理局": "出入境管理局",
    "北京市政府": "北京市政府",
    "全国企业信用信息公示系统": "全国企业信用信息公示系统",
    "工商银行": "工商银行",
    "招商银行": "招商银行",
    "建设银行": "建设银行",
    "google翻译": "Google 翻译",
    "谷歌翻译": "Google 翻译",
}

ENTITY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "possessive_target",
        re.compile(
            r"^(?:请问|请告诉我|告诉我|我想知道|我需要|帮我找|帮我看下|请帮我找)?"
            r"(?P<entity>[A-Za-z0-9.+#&\-/\s一-龥·]{2,40}?)的"
            r"(?:官方网站|官方网站|官网|官方网址|官网地址|网址|网站|官网网址|官方文档网址|官方文档|"
            r"官方帮助中心|帮助中心|客服入口|客服网站|登录入口|官网登录入口|官方登录入口|"
            r"支付入口|下载地址|官方下载地址)"
        ),
    ),
    (
        "entity_prefixed_target",
        re.compile(
            r"^(?P<entity>[A-Za-z0-9.+#&\-/\s一-龥·]{2,40}?)"
            r"(?:网页版登录入口|官网登录入口|官网登录入口|官方登录入口|官方文档网址|官方文档|"
            r"官方网站|官方网站|官方网址|官网|网址|网站|帮助中心|客服入口|下载地址|官方下载地址)"
        ),
    ),
    (
        "entity_access_region",
        re.compile(r"^(?P<entity>[A-Za-z0-9.+#&\-/\s一-龥·]{2,30}?)在国内怎么访问"),
    ),
    (
        "want_at_entity",
        re.compile(
            r"^我想在(?P<entity>[A-Za-z0-9.+#&\-/\s一-龥·]{2,30}?)"
            r"(?:买东西|购物|买书|海外购|下载|登录|注册|订票|订酒店|查|开户|投资|学习)"
        ),
    ),
    (
        "register_account",
        re.compile(
            r"^(?:怎么|如何)(?:注册|申请)(?P<entity>[A-Za-z0-9.+#&\-/\s一-龥·]{2,30}?)(?:账号|账户|帐号|信用卡)"
        ),
    ),
    (
        "download_entity",
        re.compile(r"^(?:怎么|如何)?下载(?P<entity>[A-Za-z0-9.+#&\-/\s一-龥·]{2,30}?)(?:？|\?|官网|官方网址|网站|网址|$)"),
    ),
    (
        "login_entity",
        re.compile(r"^(?:怎么|如何)(?:登录|登陆)(?P<entity>[A-Za-z0-9.+#&\-/\s一-龥·]{2,30}?)(?:？|\?|网址|网站|官网|$)"),
    ),
    (
        "after_clause_possessive",
        re.compile(
            r"(?:，|,)(?P<entity>[A-Za-z0-9.+#&\-/\s一-龥·]{2,30}?)的"
            r"(?:官方网站|官网|官方网址|网址|网站|官网登录入口|官方登录入口)"
        ),
    ),
    ("how_login_entity", re.compile(r"^(?:怎么|如何)(?:登录|登陆)(?P<entity>[A-Za-z0-9.+#&\-/\s一-龥·]{2,30}?)的")),
    (
        "query_entity",
        re.compile(
            r"^我想(?:查一下|查询|查|看一下|看下|申请)"
            r"(?P<entity>[A-Za-z0-9.+#&\-/\s一-龥·]{2,30}?)的"
        ),
    ),
    (
        "entity_before_platform",
        re.compile(
            r"^(?P<entity>[A-Za-z0-9.+#&\-/\s一-龥·]{2,30}?)"
            r"(?:商户平台|网上银行|海外购|开放平台|开发者平台)"
        ),
    ),
]

OPEN_SET_HINTS = (
    "有哪些",
    "有哪几",
    "有没有",
    "推荐几个",
    "推荐一些",
    "给我几个",
    "给我一些",
    "给我一点",
    "给我一批",
    "给我若干",
)

OPEN_SET_PREFIX_RE = re.compile(r"^(?:你知道|请问|请告诉我|告诉我|我想知道)?哪些")

IMPLAUSIBLE_ENTITY_TOKENS = (
    "哪个",
    "哪些",
    "几个",
    "一些",
    "什么",
    "哪里",
    "怎么",
    "如何",
    "推荐",
    "正规",
    "靠谱",
    "好用",
    "常用",
    "开户",
    "贷款",
    "银行官网",
    "官方网站",
    "官网",
    "网址",
    "网站",
)


def _read_text_best_effort(path: Path) -> str:
    last_error: Exception | None = None
    for encoding in READ_ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error:
        return path.read_text(encoding="utf-8", errors="replace")
    return path.read_text(encoding="utf-8")


def repair_legacy_json_text(text: str) -> tuple[str, bool]:
    repaired = text.replace("\ufeff", "").strip()
    before = repaired
    repaired = re.sub(r"(\})(\s*\{)", r"\1,\2", repaired)
    repaired = re.sub(r",(\s*])", r"\1", repaired)
    return repaired, repaired != before


def load_legacy_rows(path: Path) -> tuple[list[dict[str, Any]], bool]:
    raw_text = _read_text_best_effort(path)
    try:
        payload = json.loads(raw_text)
        if isinstance(payload, list):
            return payload, False
    except json.JSONDecodeError:
        pass

    repaired_text, repaired = repair_legacy_json_text(raw_text)
    payload = json.loads(repaired_text)
    if not isinstance(payload, list):
        raise ValueError(f"Legacy dataset must be a JSON list: {path}")
    return payload, repaired


def _clean_entity_text(value: str) -> str:
    cleaned = str(value or "").strip()
    cleaned = cleaned.replace("（", "(").replace("）", ")")
    cleaned = re.sub(r"[？?！!。，“”\"'：:、，；;]+$", "", cleaned)
    cleaned = re.sub(r"^(?:一张|一个|一家|一款|一部|一下|一些|几个|若干)\s*", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"^(?:请问|告诉我|我想|我需要)\s*", "", cleaned)
    cleaned = re.sub(r"的$", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _normalize_expected_entity(entity_text: str) -> str:
    cleaned = _clean_entity_text(entity_text)
    if not cleaned:
        return ""
    override = ENTITY_ID_OVERRIDES.get(cleaned)
    if override:
        return override
    lowered = cleaned.lower()
    override = ENTITY_ID_OVERRIDES.get(lowered)
    if override:
        return override
    if re.search(r"[\u4e00-\u9fff]", cleaned):
        return cleaned
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return lowered or cleaned


def _looks_open_set_prompt(prompt: str) -> bool:
    lowered = prompt.lower()
    return OPEN_SET_PREFIX_RE.search(prompt) is not None or any(token in prompt for token in OPEN_SET_HINTS) or any(
        token in lowered for token in ("recommend", "trustworthy", "reliable websites", "which sites")
    )


def _is_plausible_entity_text(entity_text: str) -> bool:
    cleaned = _clean_entity_text(entity_text)
    if len(cleaned) < 2 or len(cleaned) > 40:
        return False
    if any(token in cleaned for token in IMPLAUSIBLE_ENTITY_TOKENS):
        return False
    return True


def infer_expected_entity_from_prompt(prompt: str, intent: str) -> tuple[str | None, str, str]:
    if intent == "recommendation":
        return None, "none", "open_set_recommendation"

    for rule, pattern in ENTITY_PATTERNS:
        match = pattern.search(prompt)
        if match:
            entity_text = _clean_entity_text(match.group("entity"))
            if _is_plausible_entity_text(entity_text):
                return _normalize_expected_entity(entity_text), "high", rule

    return None, "none", "no_match"


def _infer_scenario(life_domain: str, intent: str) -> str:
    base = SCENARIO_BY_DOMAIN.get(life_domain, "general_web_services")
    return base


def _infer_region(life_domain: str, language: str) -> str:
    if language == "zh":
        return REGION_BY_DOMAIN.get(life_domain, "cn")
    return "global"


def migrate_legacy_rows(
    rows: list[dict[str, Any]],
    *,
    dataset_name: str,
    dataset_version: str,
    source_name: str,
    repaired_json: bool,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        prompt = str(row.get("prompt") or row.get("question") or "").strip()
        if not prompt:
            continue
        life_domain = str(row.get("domain") or row.get("life_domain") or "others").strip() or "others"
        intent = infer_intent(prompt)
        language = infer_language(prompt)
        expected_entity, guess_confidence, guess_rule = infer_expected_entity_from_prompt(prompt, intent)
        evaluation_mode = infer_evaluation_mode(intent=intent, expected_entity=expected_entity)
        if expected_entity is None and _looks_open_set_prompt(prompt):
            evaluation_mode = "open_set"
        risk_tier = infer_risk_tier(prompt, life_domain, intent)
        scenario = _infer_scenario(life_domain, intent)
        prompt_style = "legacy_natural"
        ambiguity_level = "medium" if evaluation_mode == "open_set" or expected_entity is None else "low"
        expected_count = 3 if evaluation_mode == "open_set" else None

        records.append(
            {
                "prompt_id": f"LEGACY330_{index:04d}",
                "prompt": prompt,
                "life_domain": life_domain,
                "scenario": scenario,
                "scenario_id": f"legacy330.{life_domain}.{scenario}.{intent}",
                "intent": intent,
                "risk_tier": risk_tier,
                "language": language,
                "region": _infer_region(life_domain, language),
                "evaluation_mode": evaluation_mode,
                "prompt_family": default_prompt_family(intent),
                "prompt_template_id": "legacy330.zh.raw.v1",
                "prompt_style": prompt_style,
                "ambiguity_level": ambiguity_level,
                "context_noise": "low",
                "urgency": "low",
                "expected_entity": expected_entity,
                "expected_entry_types": default_expected_entry_types(intent),
                "expected_count": expected_count,
                "tags": sorted(
                    {
                        "legacy330",
                        "legacy_migrated",
                        language,
                        life_domain,
                        prompt_style,
                        intent,
                        evaluation_mode,
                    }
                ),
                "meta": {
                    "source_name": source_name,
                    "source_index": index,
                    "source_domain": life_domain,
                    "legacy_format": True,
                    "repair_applied": repaired_json,
                    "expected_entity_guess_confidence": guess_confidence,
                    "expected_entity_guess_rule": guess_rule,
                },
            }
        )

    return {
        "dataset_name": dataset_name,
        "dataset_version": dataset_version,
        "region": "cn",
        "records": records,
        "metadata": {
            "source_name": source_name,
            "legacy_style": True,
            "repair_applied": repaired_json,
            "record_count": len(records),
        },
    }


def write_migrated_legacy_dataset(
    input_path: Path,
    output_path: Path,
    *,
    dataset_name: str = "HalluDomainBench Legacy330 Migrated",
    dataset_version: str = "0.3.0",
) -> dict[str, Any]:
    rows, repaired = load_legacy_rows(input_path)
    bundle = migrate_legacy_rows(
        rows,
        dataset_name=dataset_name,
        dataset_version=dataset_version,
        source_name=input_path.name,
        repaired_json=repaired,
    )
    write_json(output_path, bundle)
    return bundle
