"""매매 대상 종목 유니버스."""

from typing import TypedDict


class StockInfo(TypedDict):
    symbol: str
    name: str
    market: str
    sector: str


# ── 국내 (KRX) ──────────────────────────────────────────
KRX_UNIVERSE: list[StockInfo] = [
    # 반도체/IT
    {"symbol": "005930", "name": "삼성전자",       "market": "KRX", "sector": "반도체/IT"},
    {"symbol": "000660", "name": "SK하이닉스",     "market": "KRX", "sector": "반도체/IT"},
    {"symbol": "009150", "name": "삼성전기",       "market": "KRX", "sector": "반도체/IT"},
    {"symbol": "018260", "name": "삼성SDS",        "market": "KRX", "sector": "반도체/IT"},
    {"symbol": "066570", "name": "LG전자",         "market": "KRX", "sector": "반도체/IT"},
    # 인터넷/플랫폼
    {"symbol": "035420", "name": "NAVER",          "market": "KRX", "sector": "인터넷/플랫폼"},
    {"symbol": "035720", "name": "카카오",         "market": "KRX", "sector": "인터넷/플랫폼"},
    {"symbol": "293490", "name": "카카오뱅크",     "market": "KRX", "sector": "인터넷/플랫폼"},
    {"symbol": "259960", "name": "크래프톤",       "market": "KRX", "sector": "인터넷/플랫폼"},
    {"symbol": "036570", "name": "엔씨소프트",     "market": "KRX", "sector": "인터넷/플랫폼"},
    # 자동차
    {"symbol": "005380", "name": "현대차",         "market": "KRX", "sector": "자동차"},
    {"symbol": "000270", "name": "기아",           "market": "KRX", "sector": "자동차"},
    {"symbol": "012330", "name": "현대모비스",     "market": "KRX", "sector": "자동차"},
    # 배터리/화학
    {"symbol": "051910", "name": "LG화학",         "market": "KRX", "sector": "배터리/화학"},
    {"symbol": "006400", "name": "삼성SDI",        "market": "KRX", "sector": "배터리/화학"},
    {"symbol": "096770", "name": "SK이노베이션",   "market": "KRX", "sector": "배터리/화학"},
    {"symbol": "011170", "name": "롯데케미칼",     "market": "KRX", "sector": "배터리/화학"},
    # 바이오/제약
    {"symbol": "207940", "name": "삼성바이오로직스","market": "KRX", "sector": "바이오/제약"},
    {"symbol": "068270", "name": "셀트리온",       "market": "KRX", "sector": "바이오/제약"},
    {"symbol": "000100", "name": "유한양행",       "market": "KRX", "sector": "바이오/제약"},
    {"symbol": "326030", "name": "SK바이오팜",     "market": "KRX", "sector": "바이오/제약"},
    # 금융
    {"symbol": "105560", "name": "KB금융",         "market": "KRX", "sector": "금융"},
    {"symbol": "055550", "name": "신한지주",       "market": "KRX", "sector": "금융"},
    {"symbol": "086790", "name": "하나금융지주",   "market": "KRX", "sector": "금융"},
    {"symbol": "316140", "name": "우리금융지주",   "market": "KRX", "sector": "금융"},
    {"symbol": "000810", "name": "삼성화재",       "market": "KRX", "sector": "금융"},
    {"symbol": "032830", "name": "삼성생명",       "market": "KRX", "sector": "금융"},
    {"symbol": "024110", "name": "기업은행",       "market": "KRX", "sector": "금융"},
    # 통신
    {"symbol": "017670", "name": "SK텔레콤",       "market": "KRX", "sector": "통신"},
    {"symbol": "030200", "name": "KT",             "market": "KRX", "sector": "통신"},
    # 지주/대기업
    {"symbol": "003550", "name": "LG",             "market": "KRX", "sector": "지주/대기업"},
    {"symbol": "034730", "name": "SK",             "market": "KRX", "sector": "지주/대기업"},
    {"symbol": "028260", "name": "삼성물산",       "market": "KRX", "sector": "지주/대기업"},
    # 에너지/소재
    {"symbol": "010950", "name": "S-Oil",          "market": "KRX", "sector": "에너지/소재"},
    {"symbol": "010130", "name": "고려아연",       "market": "KRX", "sector": "에너지/소재"},
    {"symbol": "015760", "name": "한국전력",       "market": "KRX", "sector": "에너지/소재"},
    # 운송
    {"symbol": "003490", "name": "대한항공",       "market": "KRX", "sector": "운송"},
    {"symbol": "011200", "name": "HMM",            "market": "KRX", "sector": "운송"},
    # 엔터/게임
    {"symbol": "352820", "name": "하이브",         "market": "KRX", "sector": "엔터/게임"},
    {"symbol": "041510", "name": "SM엔터테인먼트", "market": "KRX", "sector": "엔터/게임"},
]

# ── 미국 (NASD / NYSE) ──────────────────────────────────
US_UNIVERSE: list[StockInfo] = [
    # 빅테크
    {"symbol": "AAPL",  "name": "Apple",            "market": "NASD", "sector": "빅테크"},
    {"symbol": "MSFT",  "name": "Microsoft",        "market": "NASD", "sector": "빅테크"},
    {"symbol": "GOOGL", "name": "Alphabet",         "market": "NASD", "sector": "빅테크"},
    {"symbol": "META",  "name": "Meta",             "market": "NASD", "sector": "빅테크"},
    {"symbol": "AMZN",  "name": "Amazon",           "market": "NASD", "sector": "빅테크"},
    # 반도체/AI
    {"symbol": "NVDA",  "name": "NVIDIA",           "market": "NASD", "sector": "반도체/AI"},
    {"symbol": "AMD",   "name": "AMD",              "market": "NASD", "sector": "반도체/AI"},
    {"symbol": "AVGO",  "name": "Broadcom",         "market": "NASD", "sector": "반도체/AI"},
    {"symbol": "INTC",  "name": "Intel",            "market": "NASD", "sector": "반도체/AI"},
    {"symbol": "TXN",   "name": "Texas Instruments","market": "NASD", "sector": "반도체/AI"},
    # 전기차/자동차
    {"symbol": "TSLA",  "name": "Tesla",            "market": "NASD", "sector": "전기차/자동차"},
    # 소프트웨어/클라우드
    {"symbol": "CRM",   "name": "Salesforce",       "market": "NYSE", "sector": "소프트웨어/클라우드"},
    {"symbol": "ORCL",  "name": "Oracle",           "market": "NYSE", "sector": "소프트웨어/클라우드"},
    {"symbol": "CSCO",  "name": "Cisco",            "market": "NASD", "sector": "소프트웨어/클라우드"},
    {"symbol": "ACN",   "name": "Accenture",        "market": "NYSE", "sector": "소프트웨어/클라우드"},
    # 엔터/스트리밍
    {"symbol": "NFLX",  "name": "Netflix",          "market": "NASD", "sector": "엔터/스트리밍"},
    # 금융
    {"symbol": "JPM",   "name": "JPMorgan Chase",   "market": "NYSE", "sector": "금융"},
    {"symbol": "BAC",   "name": "Bank of America",  "market": "NYSE", "sector": "금융"},
    {"symbol": "V",     "name": "Visa",             "market": "NYSE", "sector": "금융"},
    {"symbol": "MA",    "name": "Mastercard",       "market": "NYSE", "sector": "금융"},
    {"symbol": "BRK-B", "name": "Berkshire",        "market": "NYSE", "sector": "금융"},
    {"symbol": "GS",    "name": "Goldman Sachs",    "market": "NYSE", "sector": "금융"},
    # 헬스케어
    {"symbol": "UNH",   "name": "UnitedHealth",     "market": "NYSE", "sector": "헬스케어"},
    {"symbol": "LLY",   "name": "Eli Lilly",        "market": "NYSE", "sector": "헬스케어"},
    {"symbol": "JNJ",   "name": "Johnson & Johnson","market": "NYSE", "sector": "헬스케어"},
    {"symbol": "ABBV",  "name": "AbbVie",           "market": "NYSE", "sector": "헬스케어"},
    {"symbol": "MRK",   "name": "Merck",            "market": "NYSE", "sector": "헬스케어"},
    {"symbol": "TMO",   "name": "Thermo Fisher",    "market": "NYSE", "sector": "헬스케어"},
    # 소비재
    {"symbol": "WMT",   "name": "Walmart",          "market": "NYSE", "sector": "소비재"},
    {"symbol": "COST",  "name": "Costco",           "market": "NASD", "sector": "소비재"},
    {"symbol": "MCD",   "name": "McDonald's",       "market": "NYSE", "sector": "소비재"},
    {"symbol": "HD",    "name": "Home Depot",       "market": "NYSE", "sector": "소비재"},
    {"symbol": "PG",    "name": "Procter & Gamble", "market": "NYSE", "sector": "소비재"},
    {"symbol": "KO",    "name": "Coca-Cola",        "market": "NYSE", "sector": "소비재"},
    {"symbol": "PEP",   "name": "PepsiCo",          "market": "NASD", "sector": "소비재"},
    # 에너지
    {"symbol": "XOM",   "name": "ExxonMobil",       "market": "NYSE", "sector": "에너지"},
    {"symbol": "CVX",   "name": "Chevron",          "market": "NYSE", "sector": "에너지"},
    # 산업재/소재
    {"symbol": "LIN",   "name": "Linde",            "market": "NASD", "sector": "산업재/소재"},
    {"symbol": "DHR",   "name": "Danaher",          "market": "NYSE", "sector": "산업재/소재"},
    {"symbol": "NEE",   "name": "NextEra Energy",   "market": "NYSE", "sector": "산업재/소재"},
]

# 하위 호환용
UNIVERSE: list[str] = [s["symbol"] for s in KRX_UNIVERSE]
