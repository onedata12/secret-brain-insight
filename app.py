"""
시크릿 브레인 인사이트 대시보드
Streamlit 웹앱
"""

import streamlit as st
import json
import os
from datetime import datetime

# Streamlit Cloud secrets → 환경변수 주입 (로컬은 .env 사용)
try:
    if "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass

# ── 페이지 설정 ──────────────────────────────────────────
st.set_page_config(
    page_title="시크릿 브레인 인사이트 뱅크",
    page_icon="🧠",
    layout="wide"
)

# ── 모바일 최적화 CSS ────────────────────────────────────
st.markdown("""
<style>
@media (max-width: 768px) {
    .block-container {
        padding: 0.5rem !important;
        padding-top: 1rem !important;
        max-width: 100% !important;
    }
    h1 { font-size: 1.4rem !important; }
    h2 { font-size: 1.2rem !important; }
    h3 { font-size: 1.05rem !important; }
    .stTabs [data-baseweb="tab"] {
        font-size: 11px !important;
        padding: 4px 5px !important;
        min-width: 0 !important;
    }
    [data-testid="stSidebar"] { min-width: 180px !important; }
    [data-testid="column"] { gap: 0.3rem !important; }
    .stButton button { font-size: 13px !important; padding: 0.3rem 0.6rem !important; }
    .stExpander { margin-bottom: 0.5rem !important; }
}
/* 테이블 모바일 스크롤 */
table {
    display: block !important;
    overflow-x: auto !important;
    max-width: 100% !important;
    font-size: 13px !important;
    white-space: nowrap !important;
}
/* 채팅 메시지 */
[data-testid="stChatMessage"] { padding: 8px !important; }
/* 채팅 입력창 하단 고정 느낌 */
.stChatInputContainer { padding: 0.3rem !important; }
</style>
""", unsafe_allow_html=True)


# ── 윈도우 알림 헬퍼 ────────────────────────────────────
def win_notify(title: str, message: str):
    """윈도우 토스트 알림 (plyer 설치된 경우)"""
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="시크릿 브레인",
            timeout=8
        )
    except Exception:
        pass


# ── 데이터 로드/저장 헬퍼 ────────────────────────────────
def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, data):
    os.makedirs("data", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_cards():
    return load_json("data/cards.json", [])

def load_topics():
    return load_json("data/topics.json", [])

def save_topics(topics):
    save_json("data/topics.json", topics)

def update_card_status(card_id, status):
    cards = load_cards()
    for card in cards:
        if card.get("id") == card_id:
            card["status"] = status
            card["reviewed_at"] = datetime.now().isoformat()
    save_json("data/cards.json", cards)

def delete_card(card_id):
    """카드 완전 삭제"""
    cards = load_cards()
    cards = [c for c in cards if c.get("id") != card_id]
    save_json("data/cards.json", cards)

def get_review_due_cards() -> list:
    from datetime import timedelta
    cards = load_cards()
    approved = [c for c in cards if c.get("status") == "approved"]
    due = []
    now = datetime.now()
    intervals = [1, 3, 7, 14, 30]

    for card in approved:
        review_log = card.get("review_log", [])
        review_count = len(review_log)

        if review_count == 0:
            approved_at = card.get("reviewed_at") or card.get("generated_at", "")
            if approved_at:
                approved_dt = datetime.fromisoformat(approved_at[:19])
                if (now - approved_dt).days >= 1:
                    due.append(card)
        elif review_count < len(intervals):
            last_review = datetime.fromisoformat(review_log[-1][:19])
            interval = intervals[review_count]
            if (now - last_review).days >= interval:
                due.append(card)

    return due

def mark_reviewed(card_id: str):
    cards = load_cards()
    for card in cards:
        if card.get("id") == card_id:
            if "review_log" not in card:
                card["review_log"] = []
            card["review_log"].append(datetime.now().isoformat())
    save_json("data/cards.json", cards)


# ── 첫 로드시 검토 대기 알림 ─────────────────────────────
if "notified_pending" not in st.session_state:
    st.session_state["notified_pending"] = True
    _pending_count = sum(1 for c in load_cards() if c.get("status") == "pending")
    if _pending_count > 0:
        win_notify("시크릿 브레인 인사이트 뱅크", f"검토 대기 카드 {_pending_count}개가 있어요!")


# ── 사이드바 ─────────────────────────────────────────────
with st.sidebar:
    st.title("🧠 시크릿 브레인")
    st.caption("인사이트 뱅크")
    st.divider()

    page = st.radio(
        "메뉴",
        ["📥 검토 대기", "✅ 승인된 카드", "🎙️ 데일리 팟캐스트",
         "🧠 복습 & 파인만 모드", "📊 콘텐츠 뱅크", "📖 논문 원문 읽기",
         "⚙️ 주제 관리", "🚀 수집 실행"]
    )

    st.divider()
    cards = load_cards()
    pending_count = sum(1 for c in cards if c.get("status") == "pending")
    approved_count = sum(1 for c in cards if c.get("status") == "approved")
    due_cards = get_review_due_cards()
    st.metric("검토 대기", pending_count)
    st.metric("승인된 카드", approved_count)
    if due_cards:
        st.warning(f"🔔 복습 {len(due_cards)}개 대기 중")


# ── 카드 렌더링 함수 ──────────────────────────────────────

def get_trust_info(card: dict) -> dict:
    evidence = card.get("evidence_level", "")
    citations = card.get("citations", 0)

    if "메타분석" in evidence:
        base = 5
    elif "체계적 문헌고찰" in evidence:
        base = 4
    elif "무작위 대조 시험" in evidence:
        base = 3
    elif "리뷰" in evidence:
        base = 3
    else:
        base = 2

    if citations >= 500:
        base = min(base + 1, 5)
    elif citations < 20 and base > 2:
        base = base - 1

    stars = "⭐" * base + "☆" * (5 - base)
    labels = {
        5: ("🟢 매우 신뢰할 수 있음", "수백~수천 명 이상을 대상으로 여러 연구를 종합한 결과예요."),
        4: ("🟢 신뢰할 수 있음", "다수의 연구를 체계적으로 검토한 결과예요."),
        3: ("🟡 참고할 만함", "실험으로 검증된 연구지만 단일 연구예요."),
        2: ("🟠 참고용", "관찰 연구나 소규모 연구예요."),
        1: ("🔴 주의 필요", "근거가 제한적이에요. 다른 연구와 함께 참고하세요."),
    }
    label, desc = labels.get(base, labels[2])
    return {"stars": stars, "score": base, "label": label, "desc": desc}


def render_card(card, show_actions=True, show_delete=False):
    evidence = card.get("evidence_level", "📄")
    topic = card.get("topic", "")
    year = card.get("year", "")
    citations = card.get("citations", 0)
    authors = ", ".join(card.get("authors", []))
    trust = get_trust_info(card)
    card_id = card.get("id", "")

    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### {card.get('headline', '')}")
            st.caption(f"{evidence} | 📌 {topic} | {year}년 | 인용 {citations}회")
        with col2:
            if card.get("doi_url"):
                st.link_button("원문 →", card["doi_url"])

        st.markdown(f"**{trust['stars']}** &nbsp; {trust['label']}", help=trust['desc'])
        st.caption(trust['desc'])
        st.divider()

        st.markdown(f"**💡 핵심:** {card.get('one_line', '')}")

        tab1, tab2, tab3 = st.tabs(["🗣️ 쉬운 설명", "📱 SNS 문구", "🏠 랜딩 문구"])

        with tab1:
            st.info(card.get("easy_explanation", ""))
            st.markdown(f"*{card.get('why_important', '')}*")

        with tab2:
            st.success(f"**시크릿 브레인 인사이트:**\n\n{card.get('secret_brain_insight', '')}")
            st.divider()
            st.code(card.get("sns_copy", ""), language=None)
            if st.button("📋 복사", key=f"sns_{card_id}"):
                st.toast("클립보드에 복사됨!")

        with tab3:
            st.code(card.get("landing_copy", ""), language=None)
            if st.button("📋 복사", key=f"landing_{card_id}"):
                st.toast("클립보드에 복사됨!")

        keywords = card.get("keywords", [])
        if keywords:
            st.markdown(" ".join([f"`{k}`" for k in keywords]))

        with st.expander("📄 논문 정보"):
            paper_title_ko = card.get("paper_title_ko", "")
            if paper_title_ko:
                st.markdown(f"**제목:** {paper_title_ko}")
                st.caption(f"원문: {card.get('paper_title', '')}")
            else:
                st.markdown(f"**제목:** {card.get('paper_title', '')}")
            st.markdown(f"**저자:** {authors}")
            link_col1, link_col2 = st.columns(2)
            with link_col1:
                if card.get("pdf_url"):
                    st.link_button("📥 PDF 전문 무료 다운로드", card["pdf_url"], use_container_width=True)
                else:
                    st.caption("🔒 이 논문은 PDF 전문이 공개되어 있지 않아요")
            with link_col2:
                if card.get("doi_url"):
                    st.link_button("🔗 저널 페이지 바로가기", card["doi_url"], use_container_width=True)

        # ── 깊이 공부하기 ─────────────────────────────────
        with st.expander("🎓 깊이 공부하기 (AI 심층 분석)"):
            deep_title = card.get("paper_title_ko") or card.get("paper_title", "")
            st.caption(f"📄 {deep_title} — 초록 기반으로 Claude가 더 깊이 분석해줍니다")
            deep_key = f"deep_{card_id}"
            if deep_key not in st.session_state:
                if st.button("🔍 심층 분석 시작", key=f"deepbtn_{card_id}"):
                    from dotenv import load_dotenv
                    load_dotenv()
                    import anthropic as _anthropic
                    client = _anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                    prompt = f"""아래 논문 초록을 바탕으로 깊이 공부하고 싶은 사람을 위한 심층 분석을 해줘. 반말로, 친구한테 설명하듯이.
중요: 마크다운 헤더(#, ##, ###) 절대 사용하지 마. 숫자 목록과 굵은 글씨(**텍스트**)만 사용해.

논문: {card.get('paper_title', '')}
초록: {card.get('abstract_text', '')}

아래 항목으로 나눠서 설명해줘:

1. **연구 배경** - 왜 이 연구를 했을까? 어떤 문제를 풀려고 했어?
2. **연구 방법** - 어떻게 연구했어? (실험 방식, 대상, 기간 등 초록에서 읽히는 것)
3. **핵심 결과** - 구체적으로 어떤 숫자/결과가 나왔어?
4. **왜 이게 중요해?** - 이 발견이 세상에 어떤 의미야?
5. **한계점** - 이 연구에서 아쉬운 점이나 주의할 점은?
6. **더 공부하려면** - 이 주제 더 깊이 알고 싶으면 어떤 키워드로 찾아봐야 해?"""

                    with client.messages.stream(
                        model="claude-sonnet-4-6",
                        max_tokens=2500,
                        messages=[{"role": "user", "content": prompt}]
                    ) as stream:
                        result = st.write_stream(stream.text_stream)
                    st.session_state[deep_key] = result
                    if card.get("pdf_url"):
                        st.info(f"📥 더 알고 싶으면 PDF 전문을 읽어봐: [다운로드]({card['pdf_url']})")
            else:
                st.markdown(st.session_state[deep_key])
                if card.get("pdf_url"):
                    st.info(f"📥 더 알고 싶으면 PDF 전문을 읽어봐: [다운로드]({card['pdf_url']})")

        # ── 오디오 듣기 ──────────────────────────────────
        with st.expander("🔊 오디오로 듣기"):
            from audio_player import show_card_audio
            show_card_audio(card)

        # ── 초록 원문 읽기 ────────────────────────────────
        if card.get("abstract_text"):
            with st.expander("📖 초록 원문 읽기 (영어↔한국어)"):
                from paper_reader import show_paper_reader
                show_paper_reader(card)

        # ── 논문 Q&A 채팅 ─────────────────────────────────
        with st.expander("💬 이 논문에 대해 질문하기"):
            chat_key = f"chat_{card_id}"
            if chat_key not in st.session_state:
                st.session_state[chat_key] = []

            # 대화 기록 표시
            for msg in st.session_state[chat_key]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            # 예시 질문 (대화 없을 때만)
            if not st.session_state[chat_key]:
                st.caption("예시 질문:")
                ex_cols = st.columns(2)
                examples = [
                    "이 결과가 한국인에게도 적용돼?",
                    "샘플 수가 충분한 거야?",
                    "반대되는 연구도 있어?",
                    "실생활에 어떻게 적용할 수 있어?",
                ]
                for i, ex in enumerate(examples):
                    with ex_cols[i % 2]:
                        if st.button(ex, key=f"ex_{card_id}_{i}"):
                            st.session_state[chat_key].append({"role": "user", "content": ex})
                            st.session_state[f"pending_q_{card_id}"] = ex
                            st.rerun()

            # 질문 입력
            user_q = st.chat_input("궁금한 거 물어봐", key=f"input_{card_id}")
            if user_q:
                st.session_state[chat_key].append({"role": "user", "content": user_q})
                st.session_state[f"pending_q_{card_id}"] = user_q
                st.rerun()

            # 답변 생성 (스트리밍)
            pending_key = f"pending_q_{card_id}"
            if pending_key in st.session_state:
                q = st.session_state.pop(pending_key)
                from dotenv import load_dotenv
                load_dotenv()
                import anthropic as _anthropic
                client = _anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

                history = st.session_state[chat_key][:-1]
                messages = [
                    {
                        "role": "user",
                        "content": f"""너는 아래 논문을 완전히 이해한 전문가야. 일반인 친구한테 반말로 친근하게 설명해줘.
중요: 마크다운 헤더(#, ##, ###) 절대 사용하지 마. 굵은 글씨와 일반 텍스트만 써.
모르는 건 모른다고 솔직하게 말해.

논문 제목: {card.get('paper_title', '')}
논문 초록: {card.get('abstract_text', '')}
핵심 인사이트: {card.get('one_line', '')}

위 논문에 대한 질문에 답해줘."""
                    },
                    {"role": "assistant", "content": "알겠어! 이 논문에 대해 뭐든 물어봐."},
                ]
                for h in history:
                    messages.append({"role": h["role"], "content": h["content"]})
                messages.append({"role": "user", "content": q})

                with st.chat_message("assistant"):
                    with client.messages.stream(
                        model="claude-sonnet-4-6",
                        max_tokens=1500,
                        messages=messages
                    ) as stream:
                        answer = st.write_stream(stream.text_stream)
                st.session_state[chat_key].append({"role": "assistant", "content": answer})

        # ── 액션 버튼 ─────────────────────────────────────
        if show_actions and card.get("status") == "pending":
            col_a, col_b, _ = st.columns([1, 1, 3])
            with col_a:
                if st.button("✅ 승인", key=f"approve_{card_id}", type="primary"):
                    update_card_status(card_id, "approved")
                    st.rerun()
            with col_b:
                if st.button("❌ 거절", key=f"reject_{card_id}"):
                    update_card_status(card_id, "rejected")
                    st.rerun()

        if show_delete:
            if st.button("🗑️ 카드 삭제", key=f"del_{card_id}", type="secondary"):
                delete_card(card_id)
                st.rerun()


# ── 페이지: 검토 대기 ────────────────────────────────────
if page == "📥 검토 대기":
    st.title("📥 검토 대기 중인 카드")

    cards = load_cards()
    pending = [c for c in cards if c.get("status") == "pending"]

    if not pending:
        st.info("검토할 카드가 없어요. '수집 실행' 메뉴에서 논문을 수집해보세요.")
    else:
        st.caption(f"총 {len(pending)}개 카드 검토 대기 중")

        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            topics_in_pending = list(set(c.get("topic", "") for c in pending))
            selected_topic = st.selectbox("주제 필터", ["전체"] + topics_in_pending)
        with filter_col2:
            sort_option = st.selectbox("정렬", ["최신순", "오래된순", "인용수 높은순", "인용수 낮은순"])

        filtered = pending if selected_topic == "전체" else [
            c for c in pending if c.get("topic") == selected_topic
        ]

        if sort_option == "최신순":
            filtered.sort(key=lambda c: c.get("year", 0), reverse=True)
        elif sort_option == "오래된순":
            filtered.sort(key=lambda c: c.get("year", 0))
        elif sort_option == "인용수 높은순":
            filtered.sort(key=lambda c: c.get("citations", 0), reverse=True)
        elif sort_option == "인용수 낮은순":
            filtered.sort(key=lambda c: c.get("citations", 0))

        for card in filtered:
            render_card(card, show_actions=True)
            st.markdown("")


# ── 페이지: 승인된 카드 ──────────────────────────────────
elif page == "✅ 승인된 카드":
    st.title("✅ 승인된 인사이트 카드")

    cards = load_cards()
    approved = [c for c in cards if c.get("status") == "approved"]

    if not approved:
        st.info("아직 승인된 카드가 없어요.")
    else:
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            topics = list(set(c.get("topic", "") for c in approved))
            selected_topic = st.selectbox("주제 필터", ["전체"] + topics)
        with filter_col2:
            sort_option = st.selectbox("정렬", ["최신순", "오래된순", "인용수 높은순", "인용수 낮은순"])

        filtered = approved if selected_topic == "전체" else [
            c for c in approved if c.get("topic") == selected_topic
        ]

        if sort_option == "최신순":
            filtered.sort(key=lambda c: c.get("year", 0), reverse=True)
        elif sort_option == "오래된순":
            filtered.sort(key=lambda c: c.get("year", 0))
        elif sort_option == "인용수 높은순":
            filtered.sort(key=lambda c: c.get("citations", 0), reverse=True)
        elif sort_option == "인용수 낮은순":
            filtered.sort(key=lambda c: c.get("citations", 0))

        st.caption(f"{len(filtered)}개 카드")
        for card in filtered:
            render_card(card, show_actions=False, show_delete=True)


# ── 페이지: 데일리 팟캐스트 ──────────────────────────────
elif page == "🎙️ 데일리 팟캐스트":
    st.title("🎙️ 데일리 팟캐스트")
    st.caption("운동하면서, 출퇴근하면서 논문 공부")

    cards = load_cards()
    from audio_player import show_daily_podcast
    show_daily_podcast(cards)


# ── 페이지: 콘텐츠 뱅크 ─────────────────────────────────
elif page == "📊 콘텐츠 뱅크":
    st.title("📊 콘텐츠 뱅크")
    st.caption("승인된 카드의 모든 문구를 한눈에")

    cards = load_cards()
    approved = [c for c in cards if c.get("status") == "approved"]

    if not approved:
        st.info("승인된 카드가 없어요.")
    else:
        tab_sns, tab_landing, tab_insight = st.tabs(["📱 SNS 문구", "🏠 랜딩 문구", "💡 인사이트"])

        with tab_sns:
            for card in approved:
                cid = card.get("id", "")
                with st.expander(f"{card.get('headline', '')} ({card.get('topic', '')})"):
                    st.code(card.get("sns_copy", ""), language=None)
                    if st.button("🗑️ 삭제", key=f"del_sns_{cid}"):
                        delete_card(cid)
                        st.rerun()

        with tab_landing:
            for card in approved:
                cid = card.get("id", "")
                with st.expander(f"{card.get('headline', '')} ({card.get('topic', '')})"):
                    st.code(card.get("landing_copy", ""), language=None)
                    if st.button("🗑️ 삭제", key=f"del_landing_{cid}"):
                        delete_card(cid)
                        st.rerun()

        with tab_insight:
            for card in approved:
                cid = card.get("id", "")
                with st.expander(f"{card.get('headline', '')} ({card.get('topic', '')})"):
                    st.markdown(card.get("secret_brain_insight", ""))
                    if st.button("🗑️ 삭제", key=f"del_insight_{cid}"):
                        delete_card(cid)
                        st.rerun()


# ── 페이지: 복습 & 파인만 모드 ──────────────────────────
elif page == "🧠 복습 & 파인만 모드":
    st.title("🧠 복습 & 파인만 모드")

    cards = load_cards()
    approved = [c for c in cards if c.get("status") == "approved"]
    due_cards = get_review_due_cards()

    tab_review, tab_feynman = st.tabs(["🔔 복습 알림", "🎓 파인만 모드"])

    with tab_review:
        if not due_cards:
            st.success("✅ 오늘 복습할 카드가 없어! 다음 복습까지 푹 쉬어.")
            if approved:
                st.caption(f"총 {len(approved)}개 카드 관리 중")
                for card in approved:
                    log = card.get("review_log", [])
                    st.caption(f"• {card.get('headline', '')} — 복습 {len(log)}회 완료")
        else:
            st.info(f"🔔 복습할 카드 {len(due_cards)}개가 있어! 기억 굳히러 가자.")

            for card in due_cards:
                with st.container(border=True):
                    log = card.get("review_log", [])
                    review_count = len(log)
                    intervals = [1, 3, 7, 14, 30]
                    next_interval = intervals[min(review_count, len(intervals)-1)]

                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{card.get('headline', '')}**")
                        st.caption(f"{card.get('evidence_level','')} | {card.get('topic','')} | 복습 {review_count}회차")
                    with col2:
                        st.caption(f"다음 복습: {next_interval}일 후")

                    recall_key = f"recall_{card.get('id','')}"
                    if recall_key not in st.session_state:
                        st.markdown("**이 논문에서 배운 거 뭐였지? 먼저 떠올려봐 👇**")
                        recall_input = st.text_area(
                            "기억나는 대로 써봐 (틀려도 괜찮아)",
                            key=f"recall_input_{card.get('id','')}",
                            height=80,
                            placeholder="핵심 내용이 뭐였더라..."
                        )
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("✅ 확인하기", key=f"recall_check_{card.get('id','')}"):
                                st.session_state[recall_key] = recall_input or "(비워둠)"
                                st.rerun()
                        with col_b:
                            if st.button("⏭ 바로 정답 보기", key=f"skip_{card.get('id','')}"):
                                st.session_state[recall_key] = "(스킵)"
                                st.rerun()
                    else:
                        st.info(f"💡 **핵심:** {card.get('one_line', '')}")
                        st.markdown(card.get('easy_explanation', ''))

                        if st.button("✅ 복습 완료", key=f"done_{card.get('id','')}", type="primary"):
                            mark_reviewed(card.get("id",""))
                            if recall_key in st.session_state:
                                del st.session_state[recall_key]
                            st.rerun()

    with tab_feynman:
        st.markdown("**Claude가 완전히 모르는 척하고 질문을 던져. 설명하다 막히는 부분 = 아직 모르는 부분이야.**")
        st.caption("연구에 따르면 남에게 설명하는 것이 혼자 공부하는 것보다 기억 정착률이 50% 높아.")

        if not approved:
            st.info("승인된 카드가 없어요.")
        else:
            card_options = {f"{c.get('headline', c.get('paper_title','')[:30])} ({c.get('topic','')})": c for c in approved}
            selected_label = st.selectbox("어떤 논문으로 연습할까?", list(card_options.keys()))
            selected_card = card_options[selected_label]

            feynman_key = f"feynman_{selected_card.get('id','')}"
            if feynman_key not in st.session_state:
                st.session_state[feynman_key] = []

            st.divider()

            for msg in st.session_state[feynman_key]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            if not st.session_state[feynman_key]:
                st.markdown("준비되면 시작 버튼 눌러. Claude가 궁금한 척 질문 던질게.")
                if st.button("🎓 파인만 모드 시작", type="primary"):
                    st.session_state[feynman_key].append({
                        "role": "assistant",
                        "content": f"야, {selected_card.get('topic', '이 주제')} 공부했다고? 나 그거 진짜 하나도 몰라. 그게 뭔지 나한테 설명해줄 수 있어? 아주 쉽게 설명해줘."
                    })
                    st.rerun()

            if st.session_state[feynman_key]:
                col1, col2 = st.columns([4, 1])
                with col2:
                    if st.button("🔄 다시 시작"):
                        del st.session_state[feynman_key]
                        st.rerun()

            user_input = st.chat_input("설명해봐!", key=f"feynman_input_{selected_card.get('id','')}")
            if user_input and st.session_state.get(feynman_key):
                st.session_state[feynman_key].append({"role": "user", "content": user_input})

                import anthropic as _anthropic
                from dotenv import load_dotenv as _load
                _load()
                client = _anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

                system_prompt = f"""너는 아무것도 모르는 호기심 많은 친구야. 상대방이 아래 논문 내용을 설명하고 있어.
절대 정보를 먼저 알려주지 마. 오직 질문만 해. 마크다운 헤더(#, ##) 절대 쓰지 마.

전략:
- 설명이 명확하면: "오 그래서 그게 구체적으로 어떻게 되는 거야?"
- 설명이 불완전하면: "잠깐, 그 부분 이해가 안 가. 예를 들어줄 수 있어?"
- 개념이 빠지면: 모르는 척하면서 그 개념으로 유도하는 질문
- 5번 이상 대화하면: "오 이제 좀 이해됐다! 근데 그럼 일상생활에서 어떻게 써먹을 수 있어?"
- 충분히 설명하면: 칭찬하고 핵심 포인트 1개만 정리해줘

논문 내용 (너만 알고 있어, 절대 먼저 말하지 마):
제목: {selected_card.get('paper_title','')}
핵심: {selected_card.get('one_line','')}
설명: {selected_card.get('easy_explanation','')}
중요성: {selected_card.get('why_important','')}"""

                messages = [{"role": m["role"], "content": m["content"]}
                           for m in st.session_state[feynman_key]]

                with st.chat_message("assistant"):
                    with client.messages.stream(
                        model="claude-sonnet-4-6",
                        max_tokens=600,
                        system=system_prompt,
                        messages=messages
                    ) as stream:
                        answer = st.write_stream(stream.text_stream)
                st.session_state[feynman_key].append({"role": "assistant", "content": answer})
                st.rerun()


# ── 페이지: 주제 관리 ────────────────────────────────────
elif page == "⚙️ 주제 관리":
    st.title("⚙️ 주제 관리")

    topics = load_topics()

    if not topics:
        default_topics = [
            {"name": "미루기", "query": "procrastination meta-analysis psychology", "active": True},
            {"name": "실행 의도", "query": "implementation intention goal achievement meta-analysis", "active": True},
            {"name": "인지 부하", "query": "cognitive load working memory productivity meta-analysis", "active": True},
        ]
        save_topics(default_topics)
        topics = default_topics

    st.subheader("현재 주제 목록")
    for i, topic in enumerate(topics):
        col1, col2, col3 = st.columns([2, 4, 1])
        with col1:
            st.markdown(f"**{topic['name']}**")
        with col2:
            st.caption(topic.get("query", ""))
        with col3:
            if st.button("삭제", key=f"del_{i}"):
                topics.pop(i)
                save_topics(topics)
                st.rerun()

    st.divider()
    st.subheader("새 주제 추가")

    with st.form("add_topic"):
        new_name = st.text_input("주제 이름", placeholder="예: 수면과 인지능력")
        new_query = st.text_input(
            "검색 쿼리 (선택사항 — 비워두면 자동 생성)",
            placeholder="예: sleep cognitive performance meta-analysis"
        )
        st.caption("💡 검색 쿼리를 비워두면 주제 이름으로 자동 검색해요")

        if st.form_submit_button("추가하기", type="primary"):
            if new_name:
                query = new_query.strip() if new_query.strip() else f"{new_name} meta-analysis"
                topics.append({"name": new_name, "query": query, "active": True})
                save_topics(topics)
                st.success(f"'{new_name}' 주제 추가됨!")
                st.rerun()
            else:
                st.error("주제 이름을 입력해주세요.")

    st.divider()
    st.subheader("주제 예시")
    st.markdown("""
| 주제 | 검색 쿼리 예시 |
|------|--------------|
| 습관 형성 | habit formation behavior change meta-analysis |
| 수면과 성과 | sleep quality performance productivity meta-analysis |
| 운동과 뇌 | exercise cognitive function brain meta-analysis |
| 마음챙김 | mindfulness anxiety stress systematic review |
| 번아웃 | burnout prevention workplace systematic review |
| 성장 마인드셋 | growth mindset academic achievement meta-analysis |
""")


# ── 페이지: 수집 실행 ────────────────────────────────────
elif page == "🚀 수집 실행":
    st.title("🚀 논문 수집 & 카드 생성")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1단계: 논문 수집")
        st.caption("Semantic Scholar에서 메타분석 논문 수집")

        if st.button("🔍 논문 수집 시작", type="primary", use_container_width=True):
            from collector import search_papers, save_papers
            topics_check = load_topics()
            if not topics_check:
                st.error("주제가 없어요. '주제 관리' 메뉴에서 먼저 주제를 추가해주세요.")
            else:
                total_topics = len(topics_check)
                progress_bar = st.progress(0, text="논문 수집 준비 중...")
                status_box = st.status(f"논문 수집 중... (0/{total_topics} 주제)", expanded=True)
                total_added = 0
                had_error = False
                for i, topic_obj in enumerate(topics_check):
                    topic_name = topic_obj.get("name", "")
                    query = topic_obj.get("query", topic_name)
                    progress_bar.progress(
                        i / total_topics,
                        text=f"주제 {i+1}/{total_topics} 수집 중: {topic_name}"
                    )
                    status_box.write(f"🔍 **{topic_name}** 검색 중...")
                    try:
                        papers = search_papers(query)
                        added = save_papers(papers)
                        total_added += added
                        status_box.write(f"   → {len(papers)}편 검색, {added}편 신규 저장")
                    except Exception as e:
                        status_box.write(f"   ⚠️ {topic_name} 수집 오류: {e}")
                        had_error = True
                progress_bar.progress(1.0, text="수집 완료!")
                status_box.update(label=f"논문 수집 완료! ({total_added}편 신규)", state="complete")
                if not had_error:
                    st.success(f"✅ {total_added}편 신규 논문 수집 완료!")
                else:
                    st.warning(f"⚠️ 일부 오류 발생. {total_added}편 신규 논문 수집됨.")
                win_notify("논문 수집 완료", f"{total_added}편 신규 논문 수집됐어요!")

    with col2:
        st.subheader("2단계: 카드 생성")
        st.caption("Claude AI가 논문을 인사이트 카드로 변환")

        if st.button("🤖 카드 생성 시작", type="primary", use_container_width=True):
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key or api_key == "여기에_API_키_입력":
                st.error("⚠️ .env 파일에 ANTHROPIC_API_KEY를 설정해주세요!")
            else:
                all_papers = load_json("data/papers.json", [])
                existing_cards = load_cards()
                existing_card_ids = {c.get("id") for c in existing_cards}
                papers_pending = [
                    p for p in all_papers
                    if p.get("status") == "pending_explanation"
                    and p.get("paperId") not in existing_card_ids
                ]
                if not papers_pending:
                    st.info("처리할 새 논문이 없어요. 먼저 논문을 수집해주세요.")
                else:
                    from explainer import generate_card
                    total_papers = len(papers_pending)
                    progress_bar = st.progress(0, text="카드 생성 준비 중...")
                    status_box = st.status(f"AI가 카드 생성 중... (0/{total_papers})", expanded=True)
                    new_cards = []
                    for i, paper in enumerate(papers_pending):
                        title_short = (paper.get("title") or "")[:40]
                        progress_bar.progress(
                            i / total_papers,
                            text=f"카드 {i+1}/{total_papers} 생성 중: {title_short}..."
                        )
                        status_box.write(f"🤖 [{i+1}/{total_papers}] {title_short}...")
                        try:
                            card = generate_card(paper)
                            if card:
                                new_cards.append(card)
                                paper["status"] = "explained"
                                status_box.write(f"   ✅ 생성 완료")
                            else:
                                status_box.write(f"   ⏭ 건너뜀 (초록 없음)")
                        except Exception as e:
                            status_box.write(f"   ⚠️ 오류: {e}")
                    progress_bar.progress(1.0, text="카드 생성 완료!")
                    # 저장
                    if new_cards:
                        all_cards = existing_cards + new_cards
                        save_json("data/cards.json", all_cards)
                        save_json("data/papers.json", all_papers)
                    status_box.update(label=f"카드 생성 완료! ({len(new_cards)}개)", state="complete")
                    st.success(f"✅ {len(new_cards)}개 카드 생성 완료! '검토 대기' 메뉴에서 확인하세요.")
                    win_notify("카드 생성 완료", f"{len(new_cards)}개 카드가 검토 대기 중이에요!")

    st.divider()
    st.subheader("⚡ 한 번에 실행")
    if st.button("수집 + 카드 생성 한 번에", use_container_width=True):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key or api_key == "여기에_API_키_입력":
            st.error("⚠️ .env 파일에 ANTHROPIC_API_KEY를 설정해주세요!")
        else:
            from collector import search_papers, save_papers
            from explainer import generate_card

            topics_check = load_topics()
            if not topics_check:
                st.error("주제가 없어요. '주제 관리' 메뉴에서 먼저 주제를 추가해주세요.")
            else:
                # ── 1단계: 논문 수집 ──
                total_topics = len(topics_check)
                progress_bar = st.progress(0, text="논문 수집 준비 중...")
                status_box = st.status(f"1단계: 논문 수집 중... (0/{total_topics} 주제)", expanded=True)
                total_collected = 0
                for i, topic_obj in enumerate(topics_check):
                    topic_name = topic_obj.get("name", "")
                    query = topic_obj.get("query", topic_name)
                    progress_bar.progress(
                        (i / total_topics) * 0.4,
                        text=f"[수집] 주제 {i+1}/{total_topics}: {topic_name}"
                    )
                    status_box.write(f"🔍 **{topic_name}** 검색 중...")
                    try:
                        papers = search_papers(query)
                        added = save_papers(papers)
                        total_collected += added
                        status_box.write(f"   → {len(papers)}편 검색, {added}편 신규")
                    except Exception as e:
                        status_box.write(f"   ⚠️ {topic_name} 오류: {e}")
                status_box.update(label=f"1단계 완료: {total_collected}편 수집", state="complete")

                # ── 2단계: 카드 생성 ──
                all_papers = load_json("data/papers.json", [])
                existing_cards = load_cards()
                existing_card_ids = {c.get("id") for c in existing_cards}
                papers_pending = [
                    p for p in all_papers
                    if p.get("status") == "pending_explanation"
                    and p.get("paperId") not in existing_card_ids
                ]
                if papers_pending:
                    total_papers = len(papers_pending)
                    status_box2 = st.status(f"2단계: 카드 생성 중... (0/{total_papers})", expanded=True)
                    new_cards = []
                    for i, paper in enumerate(papers_pending):
                        title_short = (paper.get("title") or "")[:40]
                        progress_bar.progress(
                            0.4 + (i / total_papers) * 0.6,
                            text=f"[카드] {i+1}/{total_papers}: {title_short}..."
                        )
                        status_box2.write(f"🤖 [{i+1}/{total_papers}] {title_short}...")
                        try:
                            card = generate_card(paper)
                            if card:
                                new_cards.append(card)
                                paper["status"] = "explained"
                        except Exception as e:
                            status_box2.write(f"   ⚠️ 오류: {e}")
                    if new_cards:
                        all_cards = existing_cards + new_cards
                        save_json("data/cards.json", all_cards)
                        save_json("data/papers.json", all_papers)
                    status_box2.update(label=f"2단계 완료: {len(new_cards)}개 카드 생성", state="complete")
                    cards_made = len(new_cards)
                else:
                    cards_made = 0

                progress_bar.progress(1.0, text="모든 작업 완료!")
                st.success(f"✅ 완료! 논문 {total_collected}편 수집, 카드 {cards_made}개 생성")
                if cards_made > 0:
                    win_notify("수집 & 생성 완료", f"논문 {total_collected}편, 카드 {cards_made}개 완료!")

    st.divider()
    st.subheader("📅 자동 실행 상태")
    st.info("매일 오전 9시 자동 수집은 `scheduler.py`를 별도 터미널에서 실행해두면 작동합니다.\n\n`python scheduler.py`")

    st.subheader("📊 현황")
    cards = load_cards()
    papers = load_json("data/papers.json", [])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("수집된 논문", len(papers))
    col2.metric("생성된 카드", len(cards))
    col3.metric("검토 대기", sum(1 for c in cards if c.get("status") == "pending"))
    col4.metric("승인 완료", sum(1 for c in cards if c.get("status") == "approved"))


# ── 페이지: 논문 원문 읽기 ────────────────────────────────
elif page == "📖 논문 원문 읽기":
    from paper_reader import show_paper_reader

    st.title("📖 논문 원문 읽기")
    st.caption("왼쪽 영어에 마우스 올리면 오른쪽 번역이 하이라이트됩니다")

    cards = load_cards()
    all_cards = [c for c in cards if c.get("abstract_text")]

    if not all_cards:
        st.info("읽을 수 있는 논문이 없어요. 논문을 먼저 수집해주세요.")
    else:
        topics = sorted(set(c.get("topic", "") for c in all_cards))
        selected_topic = st.selectbox("주제 선택", ["전체"] + topics)

        filtered = all_cards if selected_topic == "전체" else [
            c for c in all_cards if c.get("topic") == selected_topic
        ]

        card_options = {f"{c.get('headline', c.get('paper_title', '')[:40])} ({c.get('evidence_level', '')})": c for c in filtered}
        selected_label = st.selectbox("논문 선택", list(card_options.keys()))
        selected_card = card_options[selected_label]

        st.divider()

        col1, col2, col3 = st.columns(3)
        col1.metric("근거 수준", selected_card.get("evidence_level", ""))
        col2.metric("인용 횟수", f"{selected_card.get('citations', 0)}회")
        col3.metric("출판 연도", f"{selected_card.get('year', '')}년")

        st.info(f"💡 **핵심:** {selected_card.get('one_line', '')}")

        st.divider()
        show_paper_reader(selected_card)
