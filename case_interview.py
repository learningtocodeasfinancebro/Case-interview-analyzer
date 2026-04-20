#!/usr/bin/env python3
"""
Case Interview Analyzer — based on Case in Point (11th Edition) by Marc Cosentino
Run: python case_interview.py
"""

import os
import sys
import json
import webbrowser
from datetime import datetime

# ── 1. Check for required packages ─────────────────────────────────────────────
try:
    import anthropic
except ImportError:
    print("\n[ERROR] The 'anthropic' package is not installed.")
    print("\nFix: open Terminal and run this command, then try again:")
    print("   pip install anthropic\n")
    sys.exit(1)

try:
    import pypdf
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    import docx
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False


# ── 2. Check for API key ────────────────────────────────────────────────────────
def get_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    print("\n[SETUP] No API key found.")
    print("Get your free key at: https://console.anthropic.com")
    print("Then paste it here (it won't be shown as you type):\n")
    import getpass
    key = getpass.getpass("API Key: ").strip()
    if not key:
        print("[ERROR] No key entered. Exiting.")
        sys.exit(1)
    print("\n[TIP] To skip this step in the future, run this in Terminal first:")
    print(f'   export ANTHROPIC_API_KEY="{key}"\n')
    return key


# ── 3. The Case in Point system prompt ─────────────────────────────────────────
SYSTEM_PROMPT = """
You are an elite consulting case interview coach with deep expertise in how BCG Korea, Bain Korea,
and McKinsey Korea actually run their case interviews. You have read 70+ real Korean office case
interview transcripts (기출) and know the exact patterns, question phrasings, and interviewer moves
each firm uses.

When given input, FIRST detect input type:
  • If input contains interview dialogue markers (ER:, EE:, 인터뷰어:, 응시자:, Q:, A:,
    면접관:, 지원자:) or reads as a back-and-forth transcript, set input_type = "transcript"
  • Otherwise set input_type = "question"

Then you MUST:
1. Identify the case type (including 비정형/Non-Standard and Guesstimation)
2. Infer which firm this case is from, if possible
3. Apply the correct framework calibrated for Korean office style
4. If input_type == "transcript": populate transcript_analysis comparing what the candidate
   actually said vs what a top candidate would say. The main output fields (clarifying_questions,
   hypothesis, workplan, recommendation_template, ceo_pitch, etc.) MUST still reflect the
   MODEL ANSWER — what the top candidate would produce — NOT what the interviewee actually did.
5. If case_type is "M&A / PE" OR the case involves PMI / 통합 / 합병 / 인수 후 통합:
   populate synergy_by_axis with 3 axes — Revenue (매출 시너지), Cost (비용 시너지),
   Strategic (전략 시너지)
6. Return a valid JSON object — NO markdown, NO extra text — ONLY the JSON

═══════════════════════════════════════════════════════
KOREAN OFFICE CONTEXT (always apply)
═══════════════════════════════════════════════════════
- Companies commonly featured: 삼성전자, 현대/기아차, SK이노베이션, LG, 배달의민족, 카카오, 네이버,
  POSCO, 4대 시중은행(KB/신한/하나/우리), 손해보험사(삼성화재/현대해상), 재벌 그룹사, 쏘카, 야놀자
- Financial units: use 억원 (100M KRW) and 조원 (1T KRW) for Korean market figures
- Profit improvement cases are the most common type (불황기/고금리 경기 맥락)
- Market entry: organic vs JV vs M&A trade-off + Korean company competitive advantage angle
  (브랜드, existing network, cost structure, 계열사 영업력)
- Regulated industries (금융, 통신, 에너지): always check feasibility/regulatory barriers FIRST
  Key regulations: 금융지주법 (금융그룹의 비금융업 진출 제한), 보험업법 (CM채널 규제),
  빅테크 보험 비교 플랫폼 수수료 규제 (~보험료의 4%), 신재생에너지 의무 비율
- Conglomerate cases: check group synergies (자회사 네트워크, 계열사 영업력)
- Card data limitation: Korean card company data only shows 결제처 + 결제금액 — NO check-in dates,
  stay duration, room type, or itemized details. Never assume granular card data exists.
- 4대 정유사: SK이노베이션, GS칼텍스, 현대오일뱅크, S-OIL — each has captive storage but outsources
  excess to ~1,000 independent 위탁저장 업체 (margin: 납사 25% > 경유 30% > 등유 20% > 아스팔트 5%)
- Auto insurance: annual renewal structure → low comparison behavior historically → 빅테크 플랫폼
  (네이버/카카오/토스) disrupting this with comparison platforms → CM channel dependency risk
- 카셰어링 (쏘카): B2B white space = 중소기업/스타트업 법인 장기 렌트(currently underserved vs
  대기업 dominated by SK네트웍스/롯데렌터카)

═══════════════════════════════════════════════════════
4대 PRIORITY INDUSTRIES (Café ICON focus — 보험 / 유통 / 자동차 / 에너지)
═══════════════════════════════════════════════════════
These four industries dominate Korean consulting case interviews. When the case maps to one,
apply the industry-specific lens below — and always use one of these four for Tier 3 industry
variants in the three_tier_progression output.

보험업 (Insurance):
  Players: 생보 (삼성생명, 교보, 한화, 신한라이프) / 손보 (삼성화재, 현대해상, DB손보, KB손보, 메리츠)
  Channels: 설계사(전속) / GA(독립채널) / TM(전화) / CM(digital direct). CM 규제 있음.
  Product mix: 자보 (연갱신, low margin, 손해율 80%+) / 장기보험 (건강·질병, high margin) / 변액·연금
  Key dynamics: 4세대 실손(2021~) 공제율 차등 / IFRS17(2023) 부채 현재가치 + KICS 자본규제 /
    빅테크 비교 플랫폼 (네이버페이·카카오페이·토스·보맵) 수수료 ~보험료 4% 상한 규제 /
    고령화 → 장수 리스크 → 종신·달러·변액 / 요양·간병·치매보험 트렌드 /
    AI 언더라이팅·손해사정 자동화로 비용 구조 경쟁.

유통업 (Retail):
  Offline: 대형마트 (이마트/홈플러스/롯데마트) / 편의점 (GS25/CU/세븐일레븐/이마트24) /
    백화점 (신세계/롯데/현대) / SSM (이마트에브리데이, 홈플러스익스프레스)
  Online: 쿠팡 (로켓배송·로켓프레시) / 네이버쇼핑 (스마트스토어 + CJ대한통운) /
    11번가·G마켓·옥션 / SSG·신세계몰 / 마켓컬리 (새벽배송)
  Vertical: 무신사 (패션) / 올리브영 (H&B 온오프 통합) / 오늘의집 (인테리어) / 크림 (리셀)
  Quick commerce: 배민B마트 / 쿠팡이츠마트 / 요마트
  Key dynamics: 대형마트 의무휴업 (월 2회) 규제 / 오프라인 구조적 하락 + 온라인 3강 (쿠팡/네이버/SSG·G마켓) /
    PB 비중 확대 (이마트 노브랜드, CU 헤이루) / 핵심 KPI = 객단가·방문빈도·GMV·재구매율·물류비/매출

자동차 (Auto):
  OEM: 현대차·기아 (국내 M/S 70%+, 글로벌 TOP 5) / 한국GM (쉐보레) / 르노코리아 / KG모빌리티 (쌍용)
  Parts: 현대모비스 (수직계열) / 만도 (ADAS) / 한온시스템 (열관리) / LG마그나 (전장)
  Battery: LG에너지솔루션·삼성SDI·SK온 (현대차와 JV·공급 관계)
  Key dynamics: ICE → BEV/PHEV 전환 (현대 E-GMP: 아이오닉5/6, EV6/EV9) /
    수출 60%+ → 미국 IRA(북미 생산 요건) + EU 탄소규제 대응 / 전기차 캐즘(2024~) 투자 부담 /
    중고차 = 엔카·케이카 + 현대차 인증중고차 직영 진출(2023) /
    모빌리티: 쏘카(카셰어링) / 타다·우티·아이엠 / 자율주행(현대-모셔널, 현대오토에버)

에너지 (Energy):
  정유 4사: SK이노베이션, GS칼텍스, 현대오일뱅크, S-OIL (마진: 납사 25% > 경유 30% > 등유 20% > 아스팔트 5%)
  전력: 한국전력 (송배전·도매 독점) + 6개 발전자회사 (한수원, 남동·중부·서부·남부·동서발전)
  가스: 한국가스공사 (LNG 도매 독점) + 도시가스사 (삼천리, 서울도시가스, 경동도시가스)
  신재생: RPS 의무비율 제도 / REC 거래 / 태양광·풍력 (해상풍력 중심)
  수소: 현대차(넥쏘) / SK E&S / 포스코홀딩스 / 두산에너빌리티(수소터빈)
  ESS·충전: LG엔솔·삼성SDI(배터리) + 한화솔루션·효성(시스템) / SK시그넷·GS커넥트·차지비·채비
  Key dynamics: 탄소중립 2050 + K-ETS 배출권거래제 / 전력요금 동결 vs 한전 누적적자 조단위 /
    RE100 대기업 수요 / SMR·그린수소 장기 베팅 / 요금 규제가 민간 진출 feasibility의 핵심 관문

═══════════════════════════════════════════════════════
FIRM-SPECIFIC STYLES (from 70+ real transcripts)
═══════════════════════════════════════════════════════

BCG Korea — Case: ~25 min 1R; 2R ~30-40 min; Final open-ended.
  STYLE: Socratic "왜?" — probes reasoning behind every choice, especially prioritization.
  Expects: stakeholder mapping (이해관계자별 journey), opportunity matrix (stakeholder × product type),
  explicit prioritization criteria (매출 임팩트 / upside / 비용 / 파트너 수용 가능성).
  Often gives data exhibits mid-case; values creativity and business judgment beyond the standard template.
  Always demands 15~30초 verbal wrap-up at case end ("짧게 결론 요약해주세요").

  BCG ROUND-SPECIFIC PATTERNS (confirmed from real transcripts):
  • 1R (~25 min): Standard case + possible bonus guesstimation sub-question at end.
    Creativity-heavy; stakeholder × product opportunity matrix on A4; prioritization explicit.
  • 2R (~30-40 min): Often opens with market mapping BEFORE framework.
    "고객 세그먼트를 먼저 한판에 그려주세요" — B2C AND B2B on one map.
    B2B further split into (company size × contract duration) 2×2 → find white space.
    If candidate only maps B2C, interviewer immediately challenges: "B2B 고객도 있지 않나요?"
  • Final (비정형): Starts with philosophical/definitional question, NOT a standard prompt.
    e.g., "배터리는 자원입니까 쓰레기입니까? 판단 기준을 먼저 세워주세요."
    Structure: Define criteria → Understand market → Value assessment. Partner co-explores
    with candidate (gives info mid-case), then asks 2-3 big questions with Socratic follow-ups.
  • PE/Acquisition cases: Use 2×2 synergy matrix (buyer's BM axes × target's product axes).
    Always clarify volume weights first (e.g., 카드:대출 = 7:3) → focus on biggest quadrant.
    Challenge: "이 전략은 인수 없이도 가능하지 않나요?" → candidate must articulate why M&A is necessary.
    Additional angle: "이 인수가 그룹 전체에는 어떤 영향?" → ecosystem / data asset angle.

  BCG SIGNATURE MOVES (watch for these):
  • "업의 본질이 무엇이라고 생각하세요?" — asks candidate to define the business before framework.
    Expected: map stakeholders (e.g., 시청자/광고주/망사업자) × value provided to each.
  • After quant answer: "이게 현실적인가요?" + "다른 방법은 없나요?" — always sanity-checks numbers
    and asks for alternatives (e.g., 가격 인하 대신 기능 추가 옵션).
  • "이 두 질문을 구분해야 할 것 같습니다 — (1) 왜 과점인가, (2) 왜 담합하는가. 어느 질문에 답하셨나요?"
    → forces candidate to be precise about which question they're actually answering.
  • "신사업/메타버스/AI" cases: repeated definition refinement — user perspective → operator
    perspective → how it differs from existing services → winning factors.
  • Cost analysis: map value chain → eliminate items comparable to competitors → trace residual
    cause (often demand forecasting failure by sales team, not production or procurement).
  • Pricing cases: present 3 methods (비용 기반 / 경쟁 기반 / 고객 WTP 기반) → select WTP →
    formula: 기존가격 + (시간절감분 × 고객 시간당 가치). e.g., 임원 연봉 10억 ÷ 연간근무시간 = 시간당 가치.
  • Mid-case scenario switch: "조건을 바꿔볼게요 — 그렇다면 어떤 회사를 사시겠습니까?" (PE cases)
  • Calculation speed: "IRR이 더 빠르지 않나요?" — prefers approximation over slow exactness.
  • Financial/insurance/platform cases: FIRST clarification must address regulation
    (금융지주법 여행업 가능 여부, CM채널 opt-in 여부, 빅테크 수수료 구조).
  • Two-part insurance platform structure: Part 1 = industry impact analysis,
    Part 2 = should client opt in? → analyze: 추가고객 × 보험료 - 수수료 vs. 종속 리스크
    (경쟁사 참여 동향 / 수수료 규제 / 플랫폼 간 경쟁 강도).

  Red flags: generic framework not tailored to this situation; only mapping B2C when B2B exists;
  answering only one of two distinct sub-questions; not catching regulatory constraint.

Bain Korea — Case: ~40 min, often complex multi-part (feasibility + market size + how).
  Style: poker-faced (표정으로 긍/부정 판단 어려움); pushes "그래서 이걸로 뭘 하신다는 건가요?"
  Expects: demand-side driver tree for market sizing (NEVER supply-side), explicit winnability
  analysis (client vs local vs global: 영업력/가격/물량/퀄리티), entry method recommendation.
  Structure: Feasibility → Market size (driver tree) → Competition → Winnability → How.

  BAIN SIGNATURE MOVES:
  • Interviewee-led format (some cases): NO direction from interviewer — candidate must drive
    the entire structure without prompting. Silence ≠ approval.
  • Risk reclassification: "이게 진짜 리스크인가요, 아니면 업계 전반의 상수인가요?"
    → candidate must distinguish true risks from industry-wide constants.
    Counter-move: use competitor benchmarking to neutralize ("Apple도 중국에서 생산하지만 리스크로
    보지 않죠 — 왜냐하면 업계 전체가 그렇게 하기 때문입니다").
  • PE M&A cases: require customer journey analysis + 5-year exit multiple calculation.
    Post-rejection pivot: "이 조건에서는 어떤 회사를 사시겠습니까?" — scenario flip test.
  • Market sizing with PTR benchmarking: when direct data unavailable, use
    Price-to-Revenue ratio from comparable markets to triangulate.
  • Water filter global market: sizing via country PTR ratios (Korea PTR as base → adjust for
    target country GDP/urbanization → derive country-level market size).
  • Customer count analysis: always split into inflow vs outflow — "유입이 줄었나요, 이탈이 늘었나요?"
  • Output clarity check: "아이디어 수준으로 원하시는 건가요, 수치 추정까지 하기를 원하시나요?"
    → standard opening clarification in Bain cases.

  Red flags: estimating from supply side; missing end-customer demand perspective;
  treating industry-wide constants as client-specific risks.

McKinsey Korea — Cases: multi-part (framework → exhibit interpretation → recommendation).
  Fit: resume + why consulting + problem-solving experience all combined.
  Style: hypothesis-driven first ("answer first"), then data; aggressively challenges assumptions;
  asks candidate to justify every claim; expects graceful recovery when challenged.

  McKINSEY SIGNATURE MOVES:
  • Opening variant: "첫 client meeting을 가게 되었는데, 질문 리스트를 뽑아봐라" — instead of framework,
    asks for a list of questions the candidate would ask the client first.
  • Problem definition: "이것이 문제입니까 아닙니까?" — candidate must set their own criteria:
    "클라이언트의 목표(수익/진료의무/연구/인력양성)가 달성되지 않으면 문제입니다."
  • Sub-question decomposition: explicitly break case into numbered sub-questions before diving in.
    e.g., "1) 자동화 가능 단계, 2) 매출/비용 변화, 3) 전략적 장단점" — show structured thinking aloud.
  • Internal vs external effects: for automation/tech cases, always analyze BOTH:
    Internal (process efficiency, cost reduction, data generation) AND
    External (고객 구매 프로세스: 결제 신속함 / 서빙 경험 향상 / 매출 향상).
    Interviewer will push: "내부 효과만 말씀하셨는데, 외부도 있지 않나요?"
  • Exhibit analysis: always give 3 insights. Structure: (1) overall pattern, (2) key anomaly/
    exception, (3) so-what implication for the client decision.
    Time-series exhibits: look for peak/off-peak variation AND supply vs demand causality.
  • Closing move: "이번 케이스 전체에서 임플리케이션을 짧게 뽑아봐라" — asks for broader
    policy/strategic implications beyond just the case answer. Many candidates miss this.
  • Information sequencing: McKinsey only reveals data when candidate asks for it.
    Must ask: "목표 수익이 얼마입니까?" to get "50억 필요한데 30억만 남" type response.
  • MAU funnel cases: 다운로드 → 오픈 → 가입시작 → 가입완료 → 활성 이용. Calculate target
    conversion rate backward from revenue goal.
  • Retail/store performance: SIZE ≠ PROFITABILITY. Insight: best stores are often smaller
    → location (입지) is the key driver, not floor space.
  • BM transformation (COVID context): monthly subscription → per-use pricing when future
    demand is unpredictable. Digital platform as hedge.
  • Dual-side market sizing: for industrial/B2B markets (e.g., ESS 윤활유), size BOTH demand
    (ESS업체수 × 액침냉각 PTR × 연간구매량 × 단가) AND supply (생산업체수 × 최대생산량 × 가동률 × 단가).
  • New market entry — layered clarification (태양광 패널 신사업 패턴):
    (1) 제품 이해: where does client's material go in the product? Is it a commodity component?
    What delivery format — 완제품/모듈/부품?
    (2) 시장 이해: B2B/B2G/B2C? Geography?
    (3) Scoping: revenue target? Is capability feasibility in scope?
    Entry method: 완제품 vs 모듈 vs 부품 납품 × JV vs M&A vs Greenfield.
    Regional prioritization: market attractiveness × competition intensity 2×2 matrix.
    Entry point: 고객단 / 채널단 / 영업단.

  Red flags: not stating hypothesis before seeing data; not re-asking when challenge misunderstood;
  only analyzing internal effects of a change; missing the closing implication question.

═══════════════════════════════════════════════════════
TRANSCRIPT MODE — when input_type == "transcript"
═══════════════════════════════════════════════════════
When input is an actual interview transcript (ER/EE dialogue), the user is studying a past case
to learn from. Your job is TWO-LAYERED:

(1) PRIMARY: produce the full model answer (all standard fields: clarifying_questions, hypothesis,
    workplan, framework, recommendation_template, ceo_pitch, etc.) — what a TOP candidate would
    have said walking into the SAME case fresh. This is the "what I wish I had said" reference.

(2) SECONDARY: fill transcript_analysis with a rigorous critique:
    • original_approach_summary: 1-2 sentences describing what the candidate actually did
    • challenge_points: for EACH interviewer pushback ("step back", "더 다룰 내용이 많다",
      "이게 현실적이냐", "업의 본질은?", 등), document (a) the ER challenge verbatim-style,
      (b) what structural mistake triggered it, (c) what a top candidate would have said instead
    • missed_opportunities: 4-6 things a top candidate would do that THIS candidate skipped —
      e.g., clarifying questions (PMI 목적 / 예산 / 기간 / 규제), hypothesis-first, Korean-market
      benchmarks (CJ ENM / 쿠팡 / 배민 / 네이버쇼핑 등), 3-axis synergy, CEO pitch with action
      items + risks, frame selection per business
    • comparison_table: 4-6 rows, each row = one aspect (Clarifying Questions, Hypothesis,
      Frame Selection, Synergy Structure, Recommendation Format, Benchmarks) with columns
      {aspect, original (what candidate did, or 'missing'), model_answer (top candidate version)}

The goal: help the user see CONCRETELY where they went wrong — not just what the right answer is.

═══════════════════════════════════════════════════════
CAFÉ ICON 3-TIER ANSWER PROGRESSION (always generate all three tiers)
═══════════════════════════════════════════════════════
Real interview competency maps to three levels. Candidates who stop at Tier 1 sound identical
to every other prep-book graduate. Tier 2 and Tier 3 are what actually earn the offer.

Tier 1 — BOOK ANSWER (Case in Point 스크립트 그대로)
  What the standard CIP framework prescribes for this case type. Safe, correct, known-good.
  This is the floor, not the ceiling. Most candidates stop here.

Tier 2 — BEYOND THE SCRIPT (CIP보다 한 발 더)
  A non-obvious insight or sharper structure that the textbook does NOT teach. Examples:
  catching a regulatory constraint before frameworking, "업의 본질" stakeholder × value mapping
  before a framework, distinguishing true risk from industry constant, external + internal
  effects split, 2×2 synergy matrix with volume weights, PTR benchmarking when direct data
  unavailable, scenario flip ("반대 조건이면 어떤 회사를 사겠나?"), dual-side market sizing.

Tier 3 — 4대 INDUSTRY VARIANT (앞서 공부한 4대 산업 내 응용)
  Reframe the same case logic inside one of the four priority industries (보험 / 유통 / 자동차 / 에너지).
  This is how interviewers generate infinite variations from one prep case — and how candidates
  prove transferable intuition. The variant MUST include a specific Korean player, regulatory
  angle, or industry metric that makes it realistic (not a generic industry swap).

This 3-tier progression IS the core training loop: memorize Tier 1, practice generating Tier 2
on any new case, rehearse Tier 3 variants across all 4 industries until case-type ↔ industry
mapping is automatic.

═══════════════════════════════════════════════════════
JSON OUTPUT SCHEMA
═══════════════════════════════════════════════════════
The JSON must have EXACTLY these keys:
{
  "input_type": "string — 'question' or 'transcript' (detected per rule above)",
  "case_type": "string — one of: Profit & Loss, Market Entry, Pricing Strategy, Growth & Sales, Competitive Response, Turnaround, M&A / PE, Guesstimation, 비정형 (Non-Standard), or Mixed",
  "firm_detected": "string — BCG, Bain, McKinsey, or Unknown",
  "key_issue": "string — one crisp sentence: the core business problem",
  "clarifying_questions": ["list of 4-6 questions — include scope, objective, and one Korean-market-specific clarification (group synergies, regulatory check, channel structure, delivery format)"],
  "hypothesis": "string — your initial hypothesis (one confident sentence). Always state one.",
  "workplan": [
    {"step": "Step 1", "action": "string — first bucket to examine and why (2 sentences)"},
    {"step": "Step 2", "action": "string — second bucket"},
    {"step": "Step 3", "action": "string — third bucket / entry method / recommendation"}
  ],
  "framework": {
    "name": "string — name of the framework",
    "buckets": [
      {"label": "string — bucket name", "questions": ["list of 3-5 analysis questions"]}
    ]
  },
  "driver_tree": {
    "applicable": true,
    "formula": "string — demand-side formula in Korean units e.g. '시장규모 = 고객수 × 연간 구매량 × 단가'",
    "sub_drivers": ["list of 3-5 key drivers with brief explanation — tie to Korean market specifics"],
    "key_driver": "string — the single most important driver and why"
  },
  "key_data_to_request": ["list of 5-8 specific data points — use 억/조 scale for Korean figures"],
  "recommendation_template": {
    "opening": "string — lead with yes/no/do it/don't",
    "reasons": ["list of 2-3 key reasons"],
    "risks": ["list of 2-3 main risks prioritized by impact x likelihood"],
    "next_steps": ["list of 2-3 next steps (short-term quick win + long-term structural)"],
    "closing_line": "string — consulting close"
  },
  "ceo_pitch": "string — 3 sentences: (1) key finding, (2) recommendation + top reason, (3) quantified impact or strategic outcome",
  "interviewer_scoring": [
    {"criterion": "string", "what_to_show": "string — what to demonstrate for this case type"}
  ],
  "pitfalls": ["list of 3-5 common mistakes on this specific case type"],
  "pattern_flags": ["list of 1-3 'if X then Y' patterns specific to this case"],
  "interviewer_guide": {
    "how_to_deliver": "string — tone, context to give, what NOT to reveal upfront",
    "hints_if_stuck": [
      {"stage": "string — e.g. 'structuring', 'market sizing', 'winnability', 'recommendation'", "hint": "string — exact words to say to nudge without giving away the answer"}
    ],
    "probing_questions": ["list of 4-5 follow-up questions to test creative thinking"],
    "green_flags": ["list of 3-4 specific behaviors that signal strong performance"],
    "red_flags": ["list of 3-4 specific warning signs of a struggling candidate"],
    "data_trap": "string — one intentional ambiguity or data trap in this case that tests whether the candidate catches it"
  },
  "interviewee_mindset": {
    "core_mindset": "string — the specific mental lens for THIS case (not generic)",
    "thinking_aloud_opening": "string — full 60-second opening script in first person",
    "time_allocation": [
      {"phase": "string", "suggested_minutes": "string", "goal": "string"}
    ],
    "beyond_the_script": ["list of 2-3 creative angles that would impress an interviewer"],
    "what_great_looks_like": "string — what separates top-tier from merely competent"
  },
  "three_tier_progression": {
    "tier_1_book_answer": "string — Tier 1: what the standard Case in Point framework prescribes for this case (baseline, everyone can do this)",
    "tier_2_beyond_script": "string — Tier 2: the non-obvious insight or sharper structure that beats the textbook (the angle that earns 'oh, interesting')",
    "tier_3_industry_variant": {
      "industry": "string — one of: 보험, 유통, 자동차, 에너지",
      "reframed_question": "string — the SAME case logic rewritten as a new question set inside this industry (include a specific Korean player)",
      "key_twist": "string — what specifically changes when the logic is applied to this industry (regulatory constraint, industry metric, player dynamic, channel structure)"
    }
  },
  "profit_diagnostic": {
    "applicable": "boolean — true ONLY if case_type is 'Profit & Loss'; if false, set all arrays below to empty []",
    "revenue_checks": ["list of 3-5 revenue-side checks covering volume/price/mix/inflow-outflow — each concrete and Korean-context aware"],
    "cost_checks": ["list of 3-5 cost-side checks covering value chain / fixed vs variable / 계열사 cost transfers"],
    "market_checks": ["list of 2-4 market/environment checks covering cycle / substitute / regulation / macro"],
    "root_cause_hypotheses": [
      {"rank": 1, "hypothesis": "string — most likely root cause of profit decline", "rationale": "string — one-line why"},
      {"rank": 2, "hypothesis": "string", "rationale": "string"},
      {"rank": 3, "hypothesis": "string", "rationale": "string"}
    ]
  },
  "transcript_analysis": {
    "applicable": "boolean — true ONLY if input_type == 'transcript'; if false, set original_approach_summary to '' and all arrays below to []",
    "original_approach_summary": "string — 1-2 sentences describing what the candidate actually did in the transcript",
    "challenge_points": [
      {"er_challenge": "string — interviewer pushback verbatim-style (e.g., 'step back 하시죠', '같은 frame으로 되겠어요?')", "why_challenged": "string — the structural mistake that triggered this pushback", "better_response": "string — what a top candidate would have said to avoid/handle it"}
    ],
    "missed_opportunities": ["list of 4-6 things a top candidate would do that THIS candidate skipped — clarifying questions, hypothesis-first, Korean benchmarks, 3-axis synergy, action-item+risk CEO pitch, frame per business"],
    "comparison_table": [
      {"aspect": "string — e.g., 'Clarifying Questions', 'Hypothesis', 'Frame Selection', 'Synergy Structure', 'Recommendation Format', 'Benchmarks'", "original": "string — what the candidate did (or 'missing')", "model_answer": "string — what the top candidate does"}
    ]
  },
  "synergy_by_axis": {
    "applicable": "boolean — true ONLY if case_type is 'M&A / PE' OR the case involves PMI/통합/합병/인수 후 통합; if false set all arrays to [] and strings to ''",
    "revenue": ["list of 2-4 revenue synergies — each specific to this case, include Korean benchmark where relevant"],
    "cost": ["list of 2-4 cost synergies"],
    "strategic": ["list of 1-3 strategic/platform synergies with Korean benchmark (e.g., CJ ENM TVING+CJ온스타일, SK네트웍스, 네이버쇼핑+스마트스토어)"],
    "lead_axis": "string — which of Revenue/Cost/Strategic is the biggest lever for THIS case; one sentence why, with quantified or directional impact"
  }
}

═══════════════════════════════════════════════════════
FRAMEWORK RULES (follow strictly)
═══════════════════════════════════════════════════════
- Profit & Loss → E(P=R-C)M: Economy/Environment first, then Revenue (volume × price × mix —
  check by channel/product/region), then Cost (fixed vs variable; COGS/SG&A/D&A), then Market.
  Korean twist: check 온라인 vs 오프라인 channel mix; check 계열사 cost transfers.
  Cost root-cause method: map full value chain → eliminate items benchmarkable to competitors →
  trace residual (often 영업팀 수요예측 실패 → 과잉생산 or 잘못된 유통).
  Cost drivers: 노선 × 노선당 운행 수 × 1회 운행당 금액 (logistics); 원재료 × 생산 × 유통 × 영업.

  PROFIT IMPROVEMENT DEEP DIVE — 불황기/고금리 케이스가 가장 많은 유형이므로 항상 full checklist로 진단:

  Revenue diagnostic:
    • Volume: 고객수 × 구매빈도 × 평균구매액 — 어느 차원이 얼마나, 언제부터 줄었나?
    • Price: 채널/상품/세그먼트별 가격 구조 — 할인 누적? 저마진 SKU로 mix shift?
    • Mix: 채널(온라인 vs 오프라인), 상품군(고마진 vs 저마진), 지역(수도권 vs 지방), 고객(신규 vs 기존)
    • Inflow vs Outflow (Bain signature): "유입이 줄었나요, 이탈이 늘었나요?" — root cause가 본질적으로 다름

  Cost diagnostic:
    • Value chain 전체 맵: 원재료 → 생산 → 물류 → 유통 → 영업 → A/S
    • 경쟁사 대비 benchmarkable items 제거 (업계 상수)
    • 남은 residual 추적 — 흔히 영업팀 수요예측 실패 → 과잉생산 or 잘못된 유통 (생산 비효율 X)
    • Fixed vs Variable: 어느 쪽이 volume에 잘못 스케일하고 있나?
    • 계열사 간 이전가격·cost transfer 검증

  Market/Environment diagnostic:
    • 업의 사이클: 성장 / 성숙 / 쇠퇴 어느 단계?
    • Substitute threat: 디지털화·DTC·플랫폼 침투로 업계 전반 마진 압축?
    • Regulation: 금융·통신·에너지면 요금·수수료 규제 변화?
    • Macro: 고금리(투자비용) / 원자재가(비용) / 환율(수출·수입)

  Root-cause prioritization (top 3):
    1) 어떤 단일 driver를 고치면 profit이 가장 크게 움직이나? (impact)
    2) 단기 (0-6개월) quick win은 무엇인가? (feasibility)
    3) 1년+ structural 개선이 필요한 것은? (long-term bet)

  Always sanity-check BEP: "이게 현실적인가요?" + propose alternative lever (BCG pattern).

- Market Entry → Feasibility (규제 FIRST for 금융/통신/에너지) → Market size (DRIVER TREE required,
  demand-side) → Market growth drivers → Competitive landscape (local vs global M/S; 과점 players;
  commodity 여부 체크) → Winnability (player × 영업력/가격/물량/퀄리티 matrix) →
  Entry method (완제품/모듈/부품 납품 × organic/JV/M&A — JV when local channel knowledge critical) →
  Regional prioritization (시장 매력도 × 경쟁강도 2×2) → Entry point (고객단/채널단/영업단) →
  Cost-Benefit. Korean twist: always include Korean company competitive advantage angle.
  New market clarification layers: (1) product role (commodity vs. key component?), (2) delivery
  format (완제품/모듈/부품), (3) B2B/B2G/B2C, (4) target geography, (5) revenue target & timeline.

- Pricing Strategy → First present 3 methods: (1) 비용 기반, (2) 경쟁 기반, (3) 고객 WTP 기반 →
  Select WTP for novel/premium products → Formula: WTP = 기존 대체재 가격 + (시간절감 × 시간당 가치)
  → 시간당 가치 = 고객 연봉 ÷ 연간 근무시간. Always sanity-check: is the price 3× realistic?
  Objective first: profit maximization / market share / ecosystem lock-in.

- Growth & Sales → Stakeholder mapping (B2C + B2B — do NOT miss B2B) →
  Opportunity matrix (stakeholder × product/service types) → White space identification →
  Prioritization (임팩트/upside/비용/파트너 수용) → Implementation sequencing.
  BCG 2R pattern: draw full market map BEFORE framework — include both current AND future customers.
  B2B segmentation: (대기업/중소기업) × (단기/장기 계약) 2×2 → find underserved quadrant.

- Competitive Response → What changed (업계 상수 vs 진짜 변화 구분) → Impact on client →
  Response options (가격/기능/채널/파트너십) → Recommendation.
  Risk test: "이게 업계 전반의 상수입니까, 우리 회사만의 리스크입니까?" — use competitor
  benchmarking to distinguish.

- Turnaround → Root cause (매출 vs 비용 vs 구조적) → Access to capital → Quick wins →
  Structural fixes → Talent. Customer analysis: always split inflow vs outflow.
  Quant sanity: after BEP calculation, always ask "이게 현실적인가?" + propose alternative lever.

- M&A / PE → Strategic fit → Market attractiveness → Target assessment →
  Synergy 2×2 matrix (buyer's BM lines × target's product lines — clarify volume weights first) →
  Valuation & synergies (in 억/조, 5-year exit multiple) → Risk & integration →
  Go/No-go + "인수 없이도 가능한 전략인가?" challenge.
  Post-acquisition: Day 0-100 plan (holding company value allocation: EBITDA × Multiple).
  Divestiture variant: Standalone EV vs Exit value — which unlocks more value?
  Scenario pivot: "이 조건에서는 어떤 회사를 살 건가요?" after initial recommendation.

  PMI / Post-Merger Integration → 3-axis synergy MANDATORY (populate synergy_by_axis):
    • Revenue synergy (매출 시너지): cross-sell, shared channels, IP leverage, shoppable content,
      platform bundling, data-driven cross-pollination
    • Cost synergy (비용 시너지): shared infrastructure (스튜디오/물류/IT), combined procurement,
      org consolidation, duplicate SG&A elimination, overlapping supplier rationalization
    • Strategic synergy (전략 시너지): ecosystem positioning (e.g., CJ ENM = TVING + CJ온스타일
      통합 플랫폼 모델), data asset consolidation, long-term moat creation, optionality
    Always identify ONE lead_axis (which synergy type is largest) and articulate it in ceo_pitch
    with quantified impact where possible (% or 억/조).

    FRAME SELECTION RULE (critical for PMI): different sub-businesses often require DIFFERENT
    frames — do NOT force one frame onto both. Examples:
      — TV홈쇼핑 / 물리적 retail → Ansoff 2×2 (기존/신규 고객 × 기존/신규 제품) + Winnability
      — 컨텐츠 / IP / 미디어 → Value Chain 확장 (기획 → 제작 → 유통 → 수익화)
      — B2B SaaS / 플랫폼 → Two-sided market growth levers (수요측 × 공급측)
      — Financial services → 채널 × 상품 × 고객 세그먼트 3축
    Using a single frame across mismatched businesses is the #1 mistake ERs flag with "업의
    본질은?" or "같은 frame으로 되겠어요?" — MECE at top level is OK, frame per bucket must fit.

- Guesstimation → Present estimate upfront → Demand-side driver tree → Round numbers →
  Sanity-check with alternative method. Korea reference: population 5,100만명, Seoul ~50%.
  WTP-based pricing guesstimation: estimate time value of money for target customer segment.
  Always clarify: (운송 대상 / 용량 / 운행 빈도 / 편도-왕복) before calculating.

- 비정형 (Non-Standard) → First: define terms and set criteria ("X의 기준은 무엇인가?") →
  Stakeholder mapping → Brainstorm opportunity space (value chain: 수거/파쇄/가공/납품 or similar) →
  Prioritize with explicit criteria → Recommend top 3.
  BCG Final pattern: partner co-explores rather than evaluating — treat as collaborative problem-solving.
  "업의 본질" opener: map (이해관계자) × (각각에 제공하는 가치) before any framework.

- Automation / Technology cases → Sub-question decomposition first (명시적으로 번호 붙여서):
  1) Which steps are automatable? 2) Revenue impact (capa) + Cost impact? 3) Strategic pros AND cons?
  Then: internal effects (process efficiency / data collection) + external effects
  (고객 구매 프로세스: 결제 신속 / 서빙 경험 / 매출 상승) — BOTH are always required.
  Machine adoption decision: financial (BEP timeline) / cross-product effects / competitive response.

DRIVER TREE RULE (required for Market Entry and Guesstimation):
- Always start from end-consumer demand (수요 측 접근) — NEVER from supply side
- Formula: Total market = # end-consumers × usage/purchase frequency × price
- For B2B/industrial markets: also build supply-side estimate as sanity check
- Identify top 1-2 KEY drivers (GDP per capita, urbanization, regulatory mandate, demographic trend)
- PTR benchmarking: when direct data unavailable, use comparable market Price-to-Revenue ratios

MECE: All framework buckets must be Mutually Exclusive, Collectively Exhaustive.

═══════════════════════════════════════════════════════
SCORING CRITERIA (always include all 4)
═══════════════════════════════════════════════════════
1. Structure of Thought — MECE, logical workplan, clear buckets; shows sub-question decomposition
2. Confidence Level — hypothesis-first, definitive language, no hedging, quick estimate before deep dive
3. Communication — workplan verbalized clearly; good clarifying questions (incl. regulatory);
   3-point exhibit reads; 15-30초 verbal wrap-up at end
4. Creativity (Café ICON 3-Tier) — Tier 1 (book answer) is the baseline only. What separates offers
   from rejections is Tier 2 (beyond the CIP script) + Tier 3 (reframe into a 4대 산업 variant —
   보험/유통/자동차/에너지 — with a specific Korean player and industry twist, not a generic swap).
   Signals: 업의 본질, white space, external + internal effects, regulatory catch, scenario flip.

RECOMMENDATION FORMAT:
- Lead with the answer (yes/no) — never bury the lede
- 2-3 reasons (most important first)
- Risks by impact × likelihood — distinguish true risks from industry constants
- Next steps: 1 short-term quick win + 1 long-term structural
- Close: "And we can help you implement that"

CEO PITCH (3 sentences):
"Our analysis shows [key finding]. We recommend [action] because [top reason].
If implemented, [quantified or strategic outcome — use 억/조 or % where possible]."
"""


# ── 4. Extract text from PDF or Word ──────────────────────────────────────────
def extract_pdf_text(pdf_path: str) -> str:
    if not PDF_SUPPORT:
        print("\n[ERROR] PDF reading requires the 'pypdf' package.")
        print("\nFix: open Terminal and run this command, then try again:")
        print("   pip install pypdf\n")
        sys.exit(1)

    pdf_path = pdf_path.strip().strip('"').strip("'")
    if not os.path.exists(pdf_path):
        print(f"\n[ERROR] File not found: {pdf_path}")
        print("Check the path and try again.\n")
        sys.exit(1)

    print(f"\nReading PDF: {os.path.basename(pdf_path)}", end="", flush=True)
    reader = pypdf.PdfReader(pdf_path)
    pages_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text)
        print(".", end="", flush=True)
    print(f" ({len(reader.pages)} pages read)\n")

    full_text = "\n\n".join(pages_text).strip()
    if not full_text:
        print("[ERROR] Could not extract text from this PDF. It may be a scanned image.")
        sys.exit(1)
    return full_text


def extract_docx_text(docx_path: str) -> str:
    if not DOCX_SUPPORT:
        print("\n[ERROR] Word file reading requires the 'python-docx' package.")
        print("\nFix: open Terminal and run this command, then try again:")
        print("   pip install python-docx\n")
        sys.exit(1)

    docx_path = docx_path.strip().strip('"').strip("'")
    if not os.path.exists(docx_path):
        print(f"\n[ERROR] File not found: {docx_path}")
        print("Check the path and try again.\n")
        sys.exit(1)

    print(f"\nReading Word file: {os.path.basename(docx_path)}...", end="", flush=True)
    doc = docx.Document(docx_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    full_text = "\n\n".join(paragraphs).strip()
    print(f" ({len(paragraphs)} paragraphs read)\n")

    if not full_text:
        print("[ERROR] Could not extract text from this Word file.")
        sys.exit(1)
    return full_text


# ── 5. Call Claude with streaming ──────────────────────────────────────────────
def analyze_case(question: str, api_key: str) -> dict:
    client = anthropic.Anthropic(api_key=api_key)

    print("\nAnalyzing your case", end="", flush=True)

    full_text = ""
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=40000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}],
    ) as stream:
        for text in stream.text_stream:
            full_text += text
            print(".", end="", flush=True)

    print(" done!\n")

    # Parse JSON from response
    try:
        clean = full_text.strip()
        # Strip markdown fences line by line (most reliable method)
        lines = clean.split("\n")
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        clean = "\n".join(lines).strip()
        # Find outermost JSON object as safety net
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start != -1 and end > start:
            clean = clean[start:end]
        data = json.loads(clean)
        return data
    except json.JSONDecodeError:
        print("[ERROR] Claude returned unexpected output. Raw response:\n")
        print(full_text[:2000])
        sys.exit(1)


# ── 6. Generate styled HTML ─────────────────────────────────────────────────────
def generate_html(question: str, data: dict, display_label: str = None) -> str:
    header_text = display_label if display_label else question

    def safe(val):
        return str(val).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Numbered bullet list (for clarifying questions)
    def numbered_list(lst, color="#2e7d32"):
        items = ""
        for i, item in enumerate(lst, 1):
            items += f"""
            <div class="num-item">
              <div class="num-circle" style="background:{color};">{i}</div>
              <div class="num-text">{safe(item)}</div>
            </div>"""
        return items

    # Icon bullet list with customizable icon + color
    def icon_list(lst, icon="•", color="#555", bg="transparent", border_color="transparent"):
        items = ""
        for item in lst:
            items += f"""
            <div class="icon-item">
              <div class="icon-bubble" style="color:{color};background:{bg};border-color:{border_color};">{icon}</div>
              <div class="icon-text">{safe(item)}</div>
            </div>"""
        return items

    # Framework buckets
    bucket_colors = ["#e94560","#f57f17","#2e7d32","#1565c0","#6a1b9a","#00695c","#bf360c","#283593"]
    buckets_html = ""
    for i, bucket in enumerate(data.get("framework", {}).get("buckets", [])):
        col = bucket_colors[i % len(bucket_colors)]
        q_html = "".join(
            f'<div class="bq-item"><span class="bq-dot" style="background:{col};"></span>{safe(q)}</div>'
            for q in bucket.get("questions", [])
        )
        buckets_html += f"""
        <div class="bucket" style="border-top:3px solid {col};">
          <div class="bucket-label" style="color:{col};">{safe(bucket.get('label',''))}</div>
          {q_html}
        </div>"""

    # Scoring criteria
    score_colors = ["#e94560","#f57f17","#2e7d32","#1565c0"]
    scoring_html = ""
    for i, item in enumerate(data.get("interviewer_scoring", [])):
        col = score_colors[i % len(score_colors)]
        scoring_html += f"""
        <div class="score-card" style="border-left:4px solid {col};">
          <div class="score-criterion" style="color:{col};">{safe(item.get('criterion',''))}</div>
          <div class="score-desc">{safe(item.get('what_to_show',''))}</div>
        </div>"""

    # Interviewer guide
    ig = data.get("interviewer_guide", {})
    hints_html = ""
    for h in ig.get("hints_if_stuck", []):
        hints_html += f"""
        <div class="hint-card">
          <div class="hint-stage">💬 {safe(h.get('stage',''))}</div>
          <div class="hint-text">"{safe(h.get('hint',''))}"</div>
        </div>"""

    green_flags_html = "".join(
        f'<div class="flag-item green-flag"><span class="flag-icon">✓</span><span class="flag-text">{safe(f)}</span></div>'
        for f in ig.get("green_flags", [])
    )
    red_flags_html = "".join(
        f'<div class="flag-item red-flag"><span class="flag-icon">✗</span><span class="flag-text">{safe(f)}</span></div>'
        for f in ig.get("red_flags", [])
    )

    # Interviewee mindset
    im = data.get("interviewee_mindset", {})
    time_rows_html = ""
    for i, t in enumerate(im.get("time_allocation", [])):
        row_bg = "#fafafa" if i % 2 else "white"
        time_rows_html += f"""
        <tr style="background:{row_bg};">
          <td class="time-min">{safe(t.get('suggested_minutes',''))}</td>
          <td class="time-phase">{safe(t.get('phase',''))}</td>
          <td class="time-goal">{safe(t.get('goal',''))}</td>
        </tr>"""

    beyond_html = "".join(
        f'<div class="beyond-item"><div class="beyond-star">★</div><div class="beyond-text">{safe(b)}</div></div>'
        for b in im.get("beyond_the_script", [])
    )

    # Café ICON 3-Tier Progression
    ttp = data.get("three_tier_progression", {}) or {}
    tier_3 = ttp.get("tier_3_industry_variant", {}) or {}
    if not isinstance(tier_3, dict):
        tier_3 = {}
    ttp_html = ""
    if ttp.get("tier_1_book_answer") or ttp.get("tier_2_beyond_script") or tier_3:
        ttp_html = f"""
    <div class="tier-card tier-1">
      <div class="tier-header">
        <span class="tier-badge tier-1-badge">Tier 1</span>
        <span class="tier-label">Book Answer — CIP 스크립트 그대로</span>
      </div>
      <div class="tier-body">{safe(ttp.get('tier_1_book_answer', ''))}</div>
    </div>
    <div class="tier-arrow">↓</div>
    <div class="tier-card tier-2">
      <div class="tier-header">
        <span class="tier-badge tier-2-badge">Tier 2</span>
        <span class="tier-label">Beyond the Script — CIP보다 한 발 더</span>
      </div>
      <div class="tier-body">{safe(ttp.get('tier_2_beyond_script', ''))}</div>
    </div>
    <div class="tier-arrow">↓</div>
    <div class="tier-card tier-3">
      <div class="tier-header">
        <span class="tier-badge tier-3-badge">Tier 3</span>
        <span class="tier-label">4대 산업 Variant — {safe(tier_3.get('industry',''))}</span>
      </div>
      <div class="tier-body">
        <div class="tier-sub-label">🔄 Reframed Question</div>
        <div class="tier-sub-content">{safe(tier_3.get('reframed_question',''))}</div>
        <div class="tier-sub-label">⚡ Key Twist</div>
        <div class="tier-sub-content">{safe(tier_3.get('key_twist',''))}</div>
      </div>
    </div>"""

    # Profit Diagnostic (conditional — only render if applicable)
    pd = data.get("profit_diagnostic", {}) or {}
    pd_applicable = pd.get("applicable") in (True, "true", "True", 1)
    pd_section_html = ""
    if pd_applicable:
        pd_revenue = icon_list(pd.get("revenue_checks", []), "₩", "#2e7d32", "#e8f5e9", "#a5d6a7")
        pd_cost = icon_list(pd.get("cost_checks", []), "−", "#e65100", "#fff3e0", "#ffcc80")
        pd_market = icon_list(pd.get("market_checks", []), "◎", "#6a1b9a", "#f3e5f5", "#ce93d8")
        rch_html = ""
        for h in pd.get("root_cause_hypotheses", []):
            rch_html += f"""
        <div class="rc-card">
          <div class="rc-rank">#{safe(h.get('rank',''))}</div>
          <div class="rc-body">
            <div class="rc-hyp">{safe(h.get('hypothesis',''))}</div>
            <div class="rc-rationale">{safe(h.get('rationale',''))}</div>
          </div>
        </div>"""
        pd_section_html = f"""
  <div class="section s15">
    <div class="section-header">
      <div class="section-icon">💰</div>
      <div class="section-title">Profit 진단 체크리스트 (Café ICON Deep Dive)</div>
    </div>
    <div class="pd-grid">
      <div class="pd-col">
        <div class="pd-col-label" style="color:#2e7d32;">매출 진단 (Revenue)</div>
        {pd_revenue}
      </div>
      <div class="pd-col">
        <div class="pd-col-label" style="color:#e65100;">비용 진단 (Cost)</div>
        {pd_cost}
      </div>
      <div class="pd-col">
        <div class="pd-col-label" style="color:#6a1b9a;">시장 진단 (Market)</div>
        {pd_market}
      </div>
    </div>
    <div class="sub-label" style="color:#bf360c;">🎯 Root Cause Hypotheses (우선순위 Top 3)</div>
    {rch_html}
  </div>"""

    # Transcript Analysis (conditional — only for input_type == "transcript")
    ta = data.get("transcript_analysis", {}) or {}
    ta_applicable = ta.get("applicable") in (True, "true", "True", 1)
    transcript_section_html = ""
    if ta_applicable:
        cp_html = ""
        for cp in ta.get("challenge_points", []):
            cp_html += f"""
        <div class="cp-card">
          <div class="cp-label">❗ 인터뷰어 챌린지</div>
          <div class="cp-challenge">"{safe(cp.get('er_challenge', ''))}"</div>
          <div class="cp-label">🔍 왜 나왔나</div>
          <div class="cp-why">{safe(cp.get('why_challenged', ''))}</div>
          <div class="cp-label">✨ 이렇게 답했어야</div>
          <div class="cp-better">{safe(cp.get('better_response', ''))}</div>
        </div>"""
        missed_html = icon_list(ta.get("missed_opportunities", []), "✗", "#c62828", "#fce4ec", "#ef9a9a")
        comparison_rows = ""
        for i, row in enumerate(ta.get("comparison_table", [])):
            row_bg = "#fafafa" if i % 2 else "white"
            comparison_rows += f"""
          <tr style="background:{row_bg};">
            <td class="cmp-aspect">{safe(row.get('aspect', ''))}</td>
            <td class="cmp-orig">{safe(row.get('original', ''))}</td>
            <td class="cmp-model">{safe(row.get('model_answer', ''))}</td>
          </tr>"""
        transcript_section_html = f"""
  <div class="section s16">
    <div class="section-header">
      <div class="section-icon">📝</div>
      <div class="section-title">Transcript Analysis — 원본 응답 vs 모범답안</div>
    </div>
    <div class="ta-summary-label">📌 응시자가 실제로 한 것</div>
    <div class="ta-summary">{safe(ta.get('original_approach_summary', ''))}</div>
    <div class="sub-label" style="color:#00695c;">❗ 인터뷰어 챌린지 포인트</div>
    {cp_html if cp_html else '<p style="color:#999;font-size:13px;">No challenges recorded.</p>'}
    <div class="sub-label" style="color:#c62828;">✗ 놓친 포인트 (Missed Opportunities)</div>
    {missed_html}
    <div class="sub-label" style="color:#1565c0;">⚖️ 비교표 — 원본 vs 모범답안</div>
    <table class="cmp-table">
      <thead><tr><th>항목</th><th>원본 응답</th><th>모범답안</th></tr></thead>
      <tbody>{comparison_rows}</tbody>
    </table>
  </div>"""

    # 3-Axis Synergy (conditional — M&A / PMI)
    sba = data.get("synergy_by_axis", {}) or {}
    sba_applicable = sba.get("applicable") in (True, "true", "True", 1)
    synergy_section_html = ""
    if sba_applicable:
        sba_revenue = icon_list(sba.get("revenue", []), "₩", "#2e7d32", "#e8f5e9", "#a5d6a7")
        sba_cost = icon_list(sba.get("cost", []), "−", "#e65100", "#fff3e0", "#ffcc80")
        sba_strategic = icon_list(sba.get("strategic", []), "◎", "#6a1b9a", "#f3e5f5", "#ce93d8")
        lead_axis = safe(sba.get("lead_axis", ""))
        synergy_section_html = f"""
  <div class="section s17">
    <div class="section-header">
      <div class="section-icon">🔗</div>
      <div class="section-title">3-Axis Synergy (M&amp;A / PMI) — 매출 · 비용 · 전략</div>
    </div>
    <div class="syn-grid">
      <div class="syn-col">
        <div class="syn-col-label" style="color:#2e7d32;">🟢 매출 시너지 (Revenue)</div>
        {sba_revenue}
      </div>
      <div class="syn-col">
        <div class="syn-col-label" style="color:#e65100;">🟡 비용 시너지 (Cost)</div>
        {sba_cost}
      </div>
      <div class="syn-col">
        <div class="syn-col-label" style="color:#6a1b9a;">🔵 전략 시너지 (Strategic)</div>
        {sba_strategic}
      </div>
    </div>
    {f'<div class="lead-axis-box"><div class="lead-axis-label">🎯 Lead Axis — 가장 큰 레버</div>{lead_axis}</div>' if lead_axis else ''}
  </div>"""

    firm_detected = safe(data.get("firm_detected", ""))
    ceo_pitch = safe(data.get("ceo_pitch", ""))
    data_trap = safe(ig.get("data_trap", ""))

    # Workplan
    workplan_html = ""
    for i, w in enumerate(data.get("workplan", []), 1):
        workplan_html += f"""
        <div class="wp-step">
          <div class="wp-num">{i}</div>
          <div class="wp-body">
            <div class="wp-label">{safe(w.get('step',''))}</div>
            <div class="wp-action">{safe(w.get('action',''))}</div>
          </div>
        </div>"""

    # Driver tree
    dt = data.get("driver_tree", {})
    dt_html = ""
    if dt.get("applicable") and dt.get("formula"):
        sub_html = icon_list(dt.get("sub_drivers", []), "→", "#6a1b9a", "#f9f0ff", "#e1bee7")
        dt_html = f"""
    <div class="dt-block">
      <div class="dt-label">📐 Driver Tree — Demand-Side Formula</div>
      <div class="dt-formula">{safe(dt.get('formula',''))}</div>
      {sub_html}
      <div class="dt-key">🔑 <strong>Key Driver:</strong> {safe(dt.get('key_driver',''))}</div>
    </div>"""

    # Recommendation
    rec = data.get("recommendation_template", {})
    reasons_html = icon_list(rec.get("reasons", []), "✓", "#2e7d32", "#e8f5e9", "#a5d6a7")
    risks_html   = icon_list(rec.get("risks", []),   "▲", "#e65100", "#fff3e0", "#ffcc80")
    nexts_html   = icon_list(rec.get("next_steps", []), "→", "#1565c0", "#e3f2fd", "#90caf9")

    rec_html = f"""
      <div class="rec-opening">{safe(rec.get('opening',''))}</div>
      <div class="rec-group">
        <div class="rec-group-label" style="color:#2e7d32;border-color:#2e7d32;">✓ Reasons</div>
        {reasons_html}
      </div>
      <div class="rec-group">
        <div class="rec-group-label" style="color:#e65100;border-color:#e65100;">▲ Risks (impact × likelihood)</div>
        {risks_html}
      </div>
      <div class="rec-group">
        <div class="rec-group-label" style="color:#1565c0;border-color:#1565c0;">→ Next Steps</div>
        {nexts_html}
      </div>
      <div class="closing-line">"{safe(rec.get('closing_line',''))}"</div>"""

    timestamp = datetime.now().strftime("%B %d, %Y — %I:%M %p")
    case_type = safe(data.get("case_type", "Unknown"))
    key_issue = safe(data.get("key_issue", ""))
    hypothesis = safe(data.get("hypothesis", ""))
    framework_name = safe(data.get("framework", {}).get("name", ""))
    firm_badge_html = (
        f'<span class="firm-badge">{firm_detected}</span>'
        if firm_detected and firm_detected != "Unknown" else ""
    )
    pitfalls_html = icon_list(data.get("pitfalls", []), "✗", "#c62828", "#fce4ec", "#ef9a9a")
    pattern_html = "".join(
        f'<span class="pattern-tag">{safe(p)}</span>' for p in data.get("pattern_flags", [])
    )
    data_tags_html = "".join(
        f'<span class="data-tag">{safe(d)}</span>' for d in data.get("key_data_to_request", [])
    )
    probing_html = icon_list(ig.get("probing_questions", []), "?", "#4527a0", "#ede7f6", "#ce93d8")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Case Analysis — {case_type}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR", sans-serif;
      background: #f0f2f5;
      color: #1a1a2e;
      padding: 28px 16px;
      font-size: 15px;
      line-height: 1.65;
    }}
    .page {{ max-width: 920px; margin: 0 auto; }}

    /* ── Header ── */
    .header {{
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      color: white;
      border-radius: 14px;
      padding: 30px 36px;
      margin-bottom: 20px;
    }}
    .header-top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
      flex-wrap: wrap;
    }}
    .header-eyebrow {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 2.5px;
      opacity: 0.5;
      margin-bottom: 6px;
    }}
    .badges {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
    .firm-badge {{
      background: rgba(255,255,255,0.18);
      border: 1px solid rgba(255,255,255,0.35);
      color: white;
      font-size: 11px; font-weight: 700;
      text-transform: uppercase; letter-spacing: 1.5px;
      padding: 5px 14px; border-radius: 20px;
    }}
    .case-type-badge {{
      background: #e94560;
      color: white;
      font-size: 11px; font-weight: 700;
      text-transform: uppercase; letter-spacing: 1.5px;
      padding: 5px 14px; border-radius: 20px;
    }}
    .question-text {{
      font-size: 20px; font-weight: 700;
      line-height: 1.5; margin-top: 18px;
    }}
    .timestamp {{ font-size: 12px; opacity: 0.4; margin-top: 10px; }}

    /* ── Section Card ── */
    .section {{
      background: white;
      border-radius: 14px;
      padding: 26px 30px;
      margin-bottom: 16px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }}
    .section-header {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 20px;
      padding-bottom: 14px;
      border-bottom: 1px solid #f0f0f0;
    }}
    .section-icon {{
      width: 36px; height: 36px;
      border-radius: 10px;
      display: flex; align-items: center; justify-content: center;
      font-size: 18px; flex-shrink: 0;
    }}
    .section-title {{
      font-size: 13px; font-weight: 800;
      text-transform: uppercase; letter-spacing: 1.2px;
    }}

    /* Section color themes */
    .s1  .section-icon {{ background:#fff3e0; }} .s1  .section-title {{ color:#e65100; }}
    .s2  .section-icon {{ background:#e8f5e9; }} .s2  .section-title {{ color:#2e7d32; }}
    .s3  .section-icon {{ background:#e3f2fd; }} .s3  .section-title {{ color:#1565c0; }}
    .s4  .section-icon {{ background:#f3e5f5; }} .s4  .section-title {{ color:#6a1b9a; }}
    .s5  .section-icon {{ background:#e0f7fa; }} .s5  .section-title {{ color:#00695c; }}
    .s6  .section-icon {{ background:#fce4ec; }} .s6  .section-title {{ color:#c62828; }}
    .s7  .section-icon {{ background:#fff8e1; }} .s7  .section-title {{ color:#f57f17; }}
    .s9  .section-icon {{ background:#ede7f6; }} .s9  .section-title {{ color:#4527a0; }}
    .s10 .section-icon {{ background:#fce4ec; }} .s10 .section-title {{ color:#c62828; }}
    .s11 .section-icon {{ background:#e0f2f1; }} .s11 .section-title {{ color:#00695c; }}
    .s12 .section-icon {{ background:#fbe9e7; }} .s12 .section-title {{ color:#bf360c; }}
    .s13 .section-icon {{ background:#e8eaf6; }} .s13 .section-title {{ color:#283593; }}

    /* ── Numbered list ── */
    .num-item {{
      display: flex; gap: 12px; align-items: flex-start;
      margin-bottom: 12px;
    }}
    .num-circle {{
      min-width: 26px; height: 26px;
      border-radius: 50%;
      color: white; font-size: 12px; font-weight: 700;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0; margin-top: 1px;
    }}
    .num-text {{ font-size: 14px; color: #333; line-height: 1.65; padding-top: 2px; }}

    /* ── Icon bullet list ── */
    .icon-item {{
      display: flex; gap: 10px; align-items: flex-start;
      margin-bottom: 10px;
    }}
    .icon-bubble {{
      min-width: 24px; height: 24px;
      border-radius: 6px; border: 1px solid;
      font-size: 13px; font-weight: 700;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0; margin-top: 1px;
    }}
    .icon-text {{ font-size: 14px; color: #333; line-height: 1.65; padding-top: 2px; }}

    /* ── Key Issue & Hypothesis ── */
    .key-issue {{
      font-size: 17px; font-weight: 600; line-height: 1.6;
      color: #1a1a2e;
      padding: 16px 20px;
      background: #fff3e0;
      border-left: 5px solid #e65100;
      border-radius: 8px;
    }}
    .hypothesis-text {{
      font-size: 15px; font-weight: 500; line-height: 1.7;
      color: #1a237e;
      padding: 16px 20px;
      background: #e8eaf6;
      border-left: 5px solid #3949ab;
      border-radius: 8px;
      font-style: italic;
    }}

    /* ── Workplan ── */
    .wp-step {{
      display: flex; gap: 16px; align-items: flex-start;
      margin-bottom: 16px; padding-bottom: 16px;
      border-bottom: 1px solid #f5f5f5;
    }}
    .wp-step:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
    .wp-num {{
      width: 32px; height: 32px; border-radius: 50%;
      background: linear-gradient(135deg, #283593, #3949ab);
      color: white; font-size: 14px; font-weight: 700;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0;
    }}
    .wp-body {{ flex: 1; }}
    .wp-label {{
      font-size: 11px; font-weight: 700;
      text-transform: uppercase; letter-spacing: 1px;
      color: #283593; margin-bottom: 4px;
    }}
    .wp-action {{ font-size: 14px; color: #333; line-height: 1.65; }}

    /* ── Framework ── */
    .framework-name {{
      display: inline-block;
      font-size: 13px; font-weight: 700;
      color: #6a1b9a; background: #f3e5f5;
      padding: 6px 16px; border-radius: 20px;
      margin-bottom: 20px;
    }}
    .buckets-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 14px;
    }}
    .bucket {{
      background: #fafafa;
      border: 1px solid #e8e8e8;
      border-radius: 10px;
      padding: 14px 16px;
    }}
    .bucket-label {{
      font-size: 12px; font-weight: 800;
      text-transform: uppercase; letter-spacing: 1px;
      margin-bottom: 12px;
    }}
    .bq-item {{
      display: flex; gap: 8px; align-items: flex-start;
      font-size: 13px; color: #444; line-height: 1.55;
      margin-bottom: 8px;
    }}
    .bq-dot {{
      width: 6px; height: 6px; border-radius: 50%;
      flex-shrink: 0; margin-top: 6px;
    }}

    /* ── Driver Tree ── */
    .dt-block {{
      background: #faf5ff;
      border: 1px solid #d1b3f0;
      border-left: 4px solid #7c3aed;
      border-radius: 10px;
      padding: 18px 20px;
      margin-top: 20px;
    }}
    .dt-label {{
      font-size: 12px; font-weight: 800;
      text-transform: uppercase; letter-spacing: 1px;
      color: #6a1b9a; margin-bottom: 12px;
    }}
    .dt-formula {{
      font-size: 15px; font-weight: 700;
      color: #4a148c;
      background: white;
      padding: 12px 16px; border-radius: 8px;
      margin-bottom: 14px;
      font-family: "Courier New", monospace;
      border: 1px solid #e1bee7;
    }}
    .dt-key {{
      font-size: 13px; color: #6a1b9a;
      background: white;
      padding: 10px 14px; border-radius: 8px;
      margin-top: 10px; border: 1px solid #e1bee7;
    }}

    /* ── Data tags ── */
    .data-tags-wrap {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .data-tag {{
      display: inline-flex; align-items: center;
      background: #e3f2fd; color: #1565c0;
      font-size: 13px; font-weight: 500;
      padding: 6px 14px; border-radius: 8px;
      border: 1px solid #90caf9;
    }}

    /* ── Recommendation ── */
    .rec-opening {{
      font-size: 17px; font-weight: 700;
      color: #c62828; background: #fce4ec;
      padding: 16px 20px; border-radius: 10px;
      border-left: 5px solid #c62828;
      margin-bottom: 20px; line-height: 1.55;
    }}
    .rec-group {{ margin-bottom: 18px; }}
    .rec-group-label {{
      font-size: 12px; font-weight: 800;
      text-transform: uppercase; letter-spacing: 1px;
      padding-bottom: 8px; margin-bottom: 10px;
      border-bottom: 2px solid;
    }}
    .closing-line {{
      font-size: 15px; font-style: italic; font-weight: 600;
      color: #c62828; text-align: center;
      padding: 16px; border: 2px dashed #e57373;
      border-radius: 10px; margin-top: 16px;
      background: #fff5f5;
    }}

    /* ── CEO Pitch ── */
    .ceo-pitch-box {{
      background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
      color: white; border-radius: 12px;
      padding: 20px 24px; margin-top: 20px;
    }}
    .ceo-pitch-label {{
      font-size: 11px; text-transform: uppercase;
      letter-spacing: 2px; opacity: 0.65; margin-bottom: 10px;
    }}
    .ceo-pitch-text {{ font-size: 15px; line-height: 1.75; font-style: italic; }}

    /* ── Scoring ── */
    .score-card {{
      padding: 14px 18px; border-radius: 8px;
      background: #fafafa; margin-bottom: 10px;
    }}
    .score-criterion {{
      font-size: 14px; font-weight: 700; margin-bottom: 5px;
    }}
    .score-desc {{ font-size: 13px; color: #555; line-height: 1.6; }}

    /* ── Pattern flags ── */
    .pattern-tag {{
      display: inline-block;
      background: #fffde7; border: 1px solid #ffd54f;
      color: #e65100; font-size: 13px;
      padding: 6px 14px; border-radius: 20px;
      margin: 4px; line-height: 1.5;
    }}

    /* ── Flags ── */
    .flag-item {{
      display: flex; gap: 10px; align-items: flex-start;
      padding: 10px 14px; border-radius: 8px;
      margin-bottom: 8px; font-size: 13px; line-height: 1.6;
    }}
    .green-flag {{ background: #f1f8e9; }}
    .red-flag   {{ background: #fce4ec; }}
    .flag-icon  {{ font-weight: 700; flex-shrink: 0; font-size: 14px; margin-top: 1px; }}
    .green-flag .flag-icon {{ color: #2e7d32; }}
    .red-flag   .flag-icon {{ color: #c62828; }}
    .flag-text  {{ color: #333; }}

    /* ── Interviewer Guide ── */
    .deliver-box {{
      background: #e0f7f4; border-left: 5px solid #00897b;
      border-radius: 8px; padding: 16px 20px;
      font-size: 14px; line-height: 1.75; color: #1a1a2e;
      margin-bottom: 20px;
    }}
    .sub-label {{
      font-size: 12px; font-weight: 800;
      text-transform: uppercase; letter-spacing: 1px;
      margin: 20px 0 12px;
    }}
    .hints-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 10px; margin-bottom: 20px;
    }}
    .hint-card {{
      background: #f9f9f9; border: 1px solid #e0e0e0;
      border-radius: 10px; padding: 14px 16px;
    }}
    .hint-stage {{
      font-size: 11px; font-weight: 700;
      text-transform: uppercase; letter-spacing: 1px;
      color: #00695c; margin-bottom: 8px;
    }}
    .hint-text {{ font-size: 13px; color: #444; line-height: 1.65; font-style: italic; }}
    .flags-row {{
      display: grid; grid-template-columns: 1fr 1fr;
      gap: 16px; margin-top: 4px;
    }}
    .flags-col-title {{
      font-size: 12px; font-weight: 800;
      text-transform: uppercase; letter-spacing: 1px;
      margin-bottom: 10px;
    }}
    .green-col .flags-col-title {{ color: #2e7d32; }}
    .red-col   .flags-col-title {{ color: #c62828; }}

    /* ── Data Trap ── */
    .data-trap-box {{
      background: #fffde7; border: 1px solid #ffd54f;
      border-left: 5px solid #f9a825; border-radius: 8px;
      padding: 14px 18px; margin-top: 18px;
      font-size: 14px; color: #5d4037; line-height: 1.65;
    }}
    .data-trap-label {{
      font-size: 11px; font-weight: 800;
      text-transform: uppercase; letter-spacing: 1px;
      color: #f57f17; margin-bottom: 6px;
    }}

    /* ── Mindset ── */
    .mindset-box {{
      background: #fff3e0; border-left: 5px solid #ef6c00;
      border-radius: 8px; padding: 16px 20px;
      font-size: 15px; font-weight: 600;
      line-height: 1.7; color: #1a1a2e; margin-bottom: 20px;
    }}
    .script-box {{
      background: #1a1a2e; color: #e8e8e8;
      border-radius: 10px; padding: 20px 24px;
      font-size: 14px; line-height: 1.85;
      font-family: Georgia, serif;
      margin-bottom: 20px; white-space: pre-wrap;
    }}
    .script-label {{
      font-size: 10px; text-transform: uppercase;
      letter-spacing: 2px; color: #888; margin-bottom: 12px;
      font-family: -apple-system, sans-serif;
    }}
    .time-table {{
      width: 100%; border-collapse: collapse;
      margin-bottom: 20px; font-size: 14px;
      border-radius: 8px; overflow: hidden;
    }}
    .time-table th {{
      background: #bf360c; color: white;
      text-align: left; padding: 10px 14px;
      font-size: 11px; text-transform: uppercase; letter-spacing: 1px;
    }}
    .time-table td {{ padding: 11px 14px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }}
    .time-table tr:last-child td {{ border-bottom: none; }}
    .time-min {{ font-weight: 700; color: #bf360c; white-space: nowrap; }}
    .time-phase {{ font-weight: 600; color: #1a1a2e; }}
    .time-goal {{ color: #555; font-size: 13px; }}
    .beyond-item {{
      display: flex; gap: 12px; align-items: flex-start;
      margin-bottom: 12px;
    }}
    .beyond-star {{ color: #ef6c00; font-size: 18px; flex-shrink: 0; }}
    .beyond-text {{ font-size: 14px; color: #333; line-height: 1.65; }}
    .great-box {{
      background: linear-gradient(135deg, #bf360c 0%, #e64a19 100%);
      color: white; border-radius: 12px;
      padding: 20px 24px; font-size: 15px; line-height: 1.75;
    }}
    .great-label {{
      font-size: 10px; text-transform: uppercase;
      letter-spacing: 2px; opacity: 0.7; margin-bottom: 10px;
    }}

    /* ── Café ICON 3-Tier Progression ── */
    .s14 .section-icon {{ background:#fff8e1; }} .s14 .section-title {{ color:#ef6c00; }}
    .tier-card {{
      border-radius: 12px;
      padding: 18px 22px;
      margin-bottom: 4px;
    }}
    .tier-1 {{ background: #f5f5f5; border-left: 5px solid #9e9e9e; }}
    .tier-2 {{ background: #e0f7f4; border-left: 5px solid #00897b; }}
    .tier-3 {{
      background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%);
      border-left: 5px solid #ff8f00;
    }}
    .tier-header {{
      display: flex; gap: 10px; align-items: center;
      margin-bottom: 10px;
    }}
    .tier-badge {{
      font-size: 10px; font-weight: 800;
      text-transform: uppercase; letter-spacing: 1.5px;
      padding: 4px 10px; border-radius: 6px;
      color: white; flex-shrink: 0;
    }}
    .tier-1-badge {{ background: #757575; }}
    .tier-2-badge {{ background: #00897b; }}
    .tier-3-badge {{ background: #ef6c00; }}
    .tier-label {{
      font-size: 12px; font-weight: 700; color: #333;
      text-transform: uppercase; letter-spacing: 1px;
    }}
    .tier-body {{
      font-size: 14px; color: #1a1a2e; line-height: 1.7;
    }}
    .tier-arrow {{
      text-align: center; font-size: 22px;
      color: #bdbdbd; margin: 2px 0;
    }}
    .tier-sub-label {{
      font-size: 11px; font-weight: 800;
      text-transform: uppercase; letter-spacing: 1px;
      color: #bf360c; margin: 12px 0 6px;
    }}
    .tier-sub-content {{
      font-size: 14px; color: #1a1a2e; line-height: 1.65;
      background: rgba(255,255,255,0.55);
      padding: 10px 14px; border-radius: 6px;
    }}

    /* ── Profit Diagnostic ── */
    .s15 .section-icon {{ background:#fce4ec; }} .s15 .section-title {{ color:#bf360c; }}
    .pd-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 14px; margin-bottom: 22px;
    }}
    .pd-col {{
      background: #fafafa; border: 1px solid #eee;
      border-radius: 10px; padding: 16px 18px;
    }}
    .pd-col-label {{
      font-size: 12px; font-weight: 800;
      text-transform: uppercase; letter-spacing: 1px;
      margin-bottom: 12px;
    }}
    .rc-card {{
      display: flex; gap: 14px; align-items: flex-start;
      background: #fff5f5; border-left: 4px solid #bf360c;
      border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;
    }}
    .rc-rank {{
      width: 30px; height: 30px; border-radius: 50%;
      background: #bf360c; color: white;
      font-size: 12px; font-weight: 800;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0;
    }}
    .rc-body {{ flex: 1; padding-top: 2px; }}
    .rc-hyp {{
      font-size: 14px; font-weight: 600;
      color: #1a1a2e; margin-bottom: 3px; line-height: 1.55;
    }}
    .rc-rationale {{
      font-size: 13px; color: #555; line-height: 1.55;
    }}

    /* ── Transcript Analysis (s16) ── */
    .s16 .section-icon {{ background:#e0f2f1; }} .s16 .section-title {{ color:#00695c; }}
    .ta-summary-label {{
      font-size: 11px; font-weight: 800;
      text-transform: uppercase; letter-spacing: 1px;
      color: #00695c; margin-bottom: 6px;
    }}
    .ta-summary {{
      font-size: 14px; color: #1a1a2e;
      background: #e0f2f1; border-left: 4px solid #00695c;
      padding: 14px 18px; border-radius: 8px;
      margin-bottom: 20px; line-height: 1.65;
    }}
    .cp-card {{
      background: #fff8e1; border: 1px solid #ffe082;
      border-left: 4px solid #f57f17; border-radius: 10px;
      padding: 14px 18px; margin-bottom: 10px;
    }}
    .cp-label {{
      font-size: 11px; font-weight: 800;
      text-transform: uppercase; letter-spacing: 1px;
      color: #bf360c; margin: 10px 0 4px;
    }}
    .cp-card .cp-label:first-child {{ margin-top: 0; }}
    .cp-challenge {{
      font-size: 14px; font-style: italic; color: #1a1a2e;
      background: white; padding: 10px 14px; border-radius: 6px;
      line-height: 1.6;
    }}
    .cp-why {{ font-size: 13px; color: #555; line-height: 1.65; }}
    .cp-better {{
      font-size: 13px; color: #1b5e20; line-height: 1.65;
      font-weight: 500; background: #f1f8e9;
      padding: 8px 12px; border-radius: 6px;
    }}
    .cmp-table {{
      width: 100%; border-collapse: collapse;
      margin-top: 10px; font-size: 13px;
      border-radius: 8px; overflow: hidden;
    }}
    .cmp-table th {{
      background: #1565c0; color: white;
      text-align: left; padding: 10px 12px;
      font-size: 11px; text-transform: uppercase; letter-spacing: 1px;
    }}
    .cmp-table td {{
      padding: 11px 12px; border-bottom: 1px solid #f0f0f0;
      vertical-align: top; line-height: 1.55;
    }}
    .cmp-table tr:last-child td {{ border-bottom: none; }}
    .cmp-aspect {{ font-weight: 700; color: #1565c0; white-space: nowrap; }}
    .cmp-orig {{ color: #c62828; }}
    .cmp-model {{ color: #2e7d32; }}

    /* ── 3-Axis Synergy (s17) ── */
    .s17 .section-icon {{ background:#e8eaf6; }} .s17 .section-title {{ color:#283593; }}
    .syn-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 14px; margin-bottom: 18px;
    }}
    .syn-col {{
      background: #fafafa; border: 1px solid #eee;
      border-radius: 10px; padding: 16px 18px;
    }}
    .syn-col-label {{
      font-size: 12px; font-weight: 800;
      text-transform: uppercase; letter-spacing: 1px;
      margin-bottom: 12px;
    }}
    .lead-axis-box {{
      background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
      color: white; border-radius: 10px;
      padding: 16px 20px; margin-top: 8px;
      font-size: 14px; line-height: 1.7;
    }}
    .lead-axis-label {{
      font-size: 11px; text-transform: uppercase;
      letter-spacing: 2px; opacity: 0.7; margin-bottom: 8px;
      font-weight: 700;
    }}

    @media print {{
      body {{ background: white; padding: 0; }}
      .section {{ box-shadow: none; border: 1px solid #e0e0e0; }}
    }}
  </style>
</head>
<body>
<div class="page">

  <!-- Header -->
  <div class="header">
    <div class="header-top">
      <div class="header-eyebrow">Case Interview Analysis</div>
      <div class="badges">
        {firm_badge_html}
        <span class="case-type-badge">{case_type}</span>
      </div>
    </div>
    <div class="question-text">{safe(header_text)}</div>
    <div class="timestamp">Generated {timestamp}</div>
  </div>
  {transcript_section_html}

  <!-- 1. Key Issue -->
  <div class="section s1">
    <div class="section-header">
      <div class="section-icon">🎯</div>
      <div class="section-title">핵심 이슈 (Key Issue)</div>
    </div>
    <div class="key-issue">{key_issue}</div>
  </div>

  <!-- 2. Clarifying Questions -->
  <div class="section s2">
    <div class="section-header">
      <div class="section-icon">❓</div>
      <div class="section-title">먼저 물어볼 Clarifying Questions</div>
    </div>
    {numbered_list(data.get('clarifying_questions', []), "#2e7d32")}
  </div>

  <!-- 3. Workplan -->
  <div class="section s13">
    <div class="section-header">
      <div class="section-icon">📋</div>
      <div class="section-title">Workplan — 첫 2분 안에 말할 내용</div>
    </div>
    {workplan_html if workplan_html else '<p style="color:#999;font-size:13px;">No workplan generated.</p>'}
  </div>

  <!-- 4. Hypothesis -->
  <div class="section s3">
    <div class="section-header">
      <div class="section-icon">💡</div>
      <div class="section-title">오프닝 가설 (Opening Hypothesis)</div>
    </div>
    <div class="hypothesis-text">{hypothesis}</div>
  </div>

  <!-- 5. Framework -->
  <div class="section s4">
    <div class="section-header">
      <div class="section-icon">🗂️</div>
      <div class="section-title">프레임워크 &amp; 구조 (MECE)</div>
    </div>
    <div class="framework-name">{framework_name}</div>
    <div class="buckets-grid">{buckets_html}</div>
    {dt_html}
  </div>
  {synergy_section_html}

  <!-- 6. Key Data -->
  <div class="section s5">
    <div class="section-header">
      <div class="section-icon">📊</div>
      <div class="section-title">케이스 중 요청할 핵심 데이터</div>
    </div>
    <div class="data-tags-wrap">{data_tags_html}</div>
  </div>

  <!-- 7. Recommendation -->
  <div class="section s6">
    <div class="section-header">
      <div class="section-icon">📣</div>
      <div class="section-title">최종 권고안 템플릿</div>
    </div>
    {rec_html}
    {f'<div class="ceo-pitch-box"><div class="ceo-pitch-label">CEO 1분 Pitch</div><div class="ceo-pitch-text">{ceo_pitch}</div></div>' if ceo_pitch else ''}
  </div>

  <!-- 8. Scoring Criteria -->
  <div class="section s7">
    <div class="section-header">
      <div class="section-icon">🏆</div>
      <div class="section-title">인터뷰어 채점 기준</div>
    </div>
    {scoring_html}
  </div>

  <!-- 9. Pattern Flags -->
  <div class="section s9">
    <div class="section-header">
      <div class="section-icon">🔍</div>
      <div class="section-title">패턴 인식 (If-Then Flags)</div>
    </div>
    <div>{pattern_html}</div>
  </div>

  <!-- 10. Pitfalls -->
  <div class="section s10">
    <div class="section-header">
      <div class="section-icon">⚠️</div>
      <div class="section-title">흔한 실수 — 피해야 할 것들</div>
    </div>
    {pitfalls_html}
  </div>

  <!-- 11. Interviewer Guide -->
  <div class="section s11">
    <div class="section-header">
      <div class="section-icon">🎙️</div>
      <div class="section-title">인터뷰어 가이드 — 케이스 진행 방법</div>
    </div>
    <div class="deliver-box">{safe(ig.get('how_to_deliver', ''))}</div>
    <div class="sub-label" style="color:#00695c;">💬 막혔을 때 줄 힌트</div>
    <div class="hints-grid">{hints_html}</div>
    <div class="sub-label" style="color:#00695c;">❓ 미드케이스 탐색 질문</div>
    <div style="margin-bottom:20px;">{probing_html}</div>
    <div class="flags-row">
      <div class="flags-col green-col">
        <div class="flags-col-title">✓ Green Flags (잘하고 있음)</div>
        {green_flags_html}
      </div>
      <div class="flags-col red-col">
        <div class="flags-col-title">✗ Red Flags (어려워하고 있음)</div>
        {red_flags_html}
      </div>
    </div>
    {f'<div class="data-trap-box"><div class="data-trap-label">⚡ Data Trap / 함정</div>{data_trap}</div>' if data_trap else ''}
  </div>

  <!-- 12. Interviewee Mindset -->
  <div class="section s12">
    <div class="section-header">
      <div class="section-icon">🧠</div>
      <div class="section-title">인터뷰이 마인드셋 — 이렇게 접근해라</div>
    </div>
    <div class="mindset-box">{safe(im.get('core_mindset', ''))}</div>
    <div class="sub-label" style="color:#bf360c;">🎤 첫 60초 스크립트 (소리내어 연습)</div>
    <div class="script-box"><div class="script-label">→ Say out loud</div>{safe(im.get('thinking_aloud_opening', ''))}</div>
    <div class="sub-label" style="color:#bf360c;">⏱️ 시간 배분</div>
    <table class="time-table">
      <thead><tr><th>시간</th><th>단계</th><th>목표</th></tr></thead>
      <tbody>{time_rows_html}</tbody>
    </table>
    <div class="sub-label" style="color:#bf360c;">★ 스크립트를 넘어서 — 차별화 포인트</div>
    <div style="margin-bottom:20px;">{beyond_html}</div>
    <div class="great-box">
      <div class="great-label">Top-Tier 답변이란?</div>
      {safe(im.get('what_great_looks_like', ''))}
    </div>
  </div>
  {pd_section_html}

  <!-- 13. Café ICON 3-Tier Progression -->
  <div class="section s14">
    <div class="section-header">
      <div class="section-icon">🪜</div>
      <div class="section-title">Café ICON 3-Tier 답변 계단 — Tier 1 → 2 → 3</div>
    </div>
    {ttp_html if ttp_html else '<p style="color:#999;font-size:13px;">No three-tier progression generated.</p>'}
  </div>

</div>
</body>
</html>"""
    return html


# ── 7. Save HTML and open in browser ───────────────────────────────────────────
def save_and_open(question: str, html: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        f"case_analysis_{timestamp}.html"
    )
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    return filename


# ── 8. Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  CASE INTERVIEW ANALYZER")
    print("  Based on Case in Point (11th Ed.) by Marc Cosentino")
    print("=" * 60)

    # Get API key
    api_key = get_api_key()

    # Choose input method
    print("\nHow would you like to input the case?")
    print("  [1] Type / paste a question")
    file_note_parts = []
    if not PDF_SUPPORT:
        file_note_parts.append("PDF requires: pip install pypdf")
    if not DOCX_SUPPORT:
        file_note_parts.append("Word requires: pip install python-docx")
    file_note = f" ({', '.join(file_note_parts)})" if file_note_parts else ""
    print(f"  [2] Load from a file (PDF or Word .docx){file_note}")
    print()
    choice = input("Enter 1 or 2: ").strip()

    question = ""
    display_label = None

    if choice == "2":
        print("\nDrag the file into this Terminal window (or type the full path):")
        print("Supported: .pdf  .docx")
        file_path = input("File path: ").strip().strip('"').strip("'")
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".docx":
            question = extract_docx_text(file_path)
            display_label = f"📄 {os.path.basename(file_path)}"
        else:
            question = extract_pdf_text(file_path)
            display_label = f"📄 {os.path.basename(file_path)}"
    else:
        print("\nPaste your case question below.")
        print("(You can paste multiple lines — press Enter twice when done)\n")
        lines = []
        while True:
            try:
                line = input()
                if line == "" and lines and lines[-1] == "":
                    break
                lines.append(line)
            except EOFError:
                break
        question = "\n".join(lines).strip()

    if not question:
        print("[ERROR] No input provided. Exiting.")
        sys.exit(1)

    # Analyze
    data = analyze_case(question, api_key)

    # Generate HTML
    html = generate_html(question, data, display_label=display_label)

    # Save and open
    filepath = save_and_open(question, html)
    print(f"Saved: {filepath}")
    print("Opening in your browser...\n")
    webbrowser.open(f"file://{filepath}")

    print("Done! Your case analysis is open in the browser.")
    print("The file is saved at:")
    print(f"  {filepath}\n")


if __name__ == "__main__":
    main()
