import re

# Patterns that indicate prompt injection attempts
INJECTION_PATTERNS = [
    r"忽略(之前|上面|以前)(的|所有)?(指令|提示|规则|prompt)",
    r"ignore\s+(previous|above|all)\s+(instructions?|prompts?|rules?)",
    r"你(现在)?(是|扮演|假装)(一个|成为)",
    r"you\s+are\s+now\s+(a|an|the)",
    r"(system|系统)\s*(prompt|提示)",
    r"repeat\s+(after\s+me|the\s+(system|above))",
    r"(DAN|jailbreak|越狱|突破限制)",
    r"(假装|模拟|扮演).*(没有|不受).*(限制|约束|规则)",
]

# Sensitive words that trigger human handoff
SENSITIVE_KEYWORDS = [
    "投诉", "退款", "退货", "纠纷", "假货", "质疑真假",
    "维权", "法律", "起诉", "律师", "工商",
    "定制设计", "私人定制", "特殊工艺", "来图定制",
    "大额议价", "最低价", "渠道价", "代理价", "批发价",
    "合作政策", "加盟", "代理",
]

# Patterns for price/inventory claims AI must not make
FORBIDDEN_CLAIMS = [
    r"(保证|承诺|确保)(保值|升值|增值)",
    r"(绝对|肯定|一定)(是真|是正品|没有问题)",
    r"(最便宜|最低价|全网最低|没有更便宜)",
    r"(无限量|大量库存|库存充足)(?!.*知识库)",
]


def detect_prompt_injection(query: str) -> bool:
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            return True
    return False


def detect_sensitive_words(query: str) -> bool:
    for keyword in SENSITIVE_KEYWORDS:
        if keyword in query:
            return True
    return False


def check_forbidden_claims(response: str) -> bool:
    for pattern in FORBIDDEN_CLAIMS:
        if re.search(pattern, response, re.IGNORECASE):
            return True
    return False


def sanitize_response(response: str) -> str:
    if check_forbidden_claims(response):
        return "抱歉，这个问题需要人工客服为您准确解答，我已帮您转接人工。"
    return response


def should_force_handoff(query: str) -> tuple[bool, str]:
    if detect_prompt_injection(query):
        return True, "检测到异常输入，已转接人工客服"
    if detect_sensitive_words(query):
        return True, "涉及敏感话题，已转接人工客服"
    return False, ""
