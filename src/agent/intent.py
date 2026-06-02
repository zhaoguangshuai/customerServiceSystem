from enum import Enum


class Intent(str, Enum):
    PRODUCT_INQUIRY = "product_inquiry"
    PRICE_INQUIRY = "price_inquiry"
    AFTER_SALES = "after_sales"
    CUSTOM_ORDER = "custom_order"
    COMPLAINT = "complaint"
    PRICE_NEGOTIATION = "price_negotiation"
    GENERAL = "general"
    UNKNOWN = "unknown"


# Keywords mapped to intents
INTENT_KEYWORDS = {
    Intent.PRODUCT_INQUIRY: [
        "黄金", "钻石", "彩宝", "银饰", "款式", "新品", "爆款",
        "项链", "戒指", "手镯", "耳环", "吊坠", "手链",
        "18K", "24K", "足金", "铂金", "翡翠", "珍珠",
    ],
    Intent.PRICE_INQUIRY: [
        "价格", "多少钱", "报价", "什么价", "几钱", "价位",
        "克价", "工费", "金价",
    ],
    Intent.AFTER_SALES: [
        "售后", "维修", "保养", "清洗", "换款", "质量问题",
    ],
    Intent.CUSTOM_ORDER: [
        "定制", "定做", "来图", "私人定制", "特殊工艺", "非标",
    ],
    Intent.COMPLAINT: [
        "投诉", "退款", "退货", "纠纷", "不满意", "假货",
    ],
    Intent.PRICE_NEGOTIATION: [
        "便宜", "优惠", "折扣", "最低价", "打折", "议价",
        "能不能少", "能不能便宜", "再低点",
    ],
}

INTENT_PRIORITY = {
    Intent.COMPLAINT: 50,
    Intent.PRICE_NEGOTIATION: 40,
    Intent.CUSTOM_ORDER: 30,
    Intent.PRICE_INQUIRY: 20,
    Intent.AFTER_SALES: 10,
    Intent.PRODUCT_INQUIRY: 0,
}


def classify_intent(query: str) -> Intent:
    scores: dict[Intent, int] = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in query)
        if score > 0:
            scores[intent] = score

    if not scores:
        return Intent.GENERAL

    return max(scores, key=lambda intent: (scores[intent], INTENT_PRIORITY.get(intent, 0)))


def needs_human_handoff(intent: Intent) -> bool:
    return intent in (
        Intent.COMPLAINT,
        Intent.PRICE_NEGOTIATION,
        Intent.CUSTOM_ORDER,
    )
