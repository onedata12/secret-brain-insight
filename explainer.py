"""
논문 해설기 - Claude API
논문 abstract를 친근한 인사이트 카드로 변환
"""

import sys
import anthropic
import json
import os
from datetime import datetime
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()


def generate_card(paper: dict) -> dict | None:
    """논문 한 편을 인사이트 카드로 변환"""

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    title = paper.get("title", "")
    abstract = paper.get("abstract", "")
    year = paper.get("year", "")
    citations = paper.get("citationCount", 0)
    evidence_level = paper.get("evidence_level", "📄 논문")
    topic = paper.get("search_topic", "")

    if not abstract:
        return None

    prompt = f"""너는 복잡한 논문을 친한 친구처럼 쉽게 설명해주는 전문가야.
아래 논문을 읽고 인사이트 카드를 만들어줘.

**논문 정보**
- 제목: {title}
- 출판 연도: {year}
- 인용 수: {citations}회
- 근거 수준: {evidence_level}
- 주제: {topic}
- 초록: {abstract}

**아래 JSON 형식으로만 응답해. 다른 텍스트 없이 JSON만.**

{{
  "headline": "논문을 한 줄로 표현한 임팩트 있는 제목 (20자 이내, 말투: ~야/~해/~거야)",
  "one_line": "핵심 발견을 한 문장으로 (숫자/통계 포함하면 더 좋아)",
  "easy_explanation": "친한 친구한테 설명하듯이 3~4문장으로. 반말. 비유 써도 돼. 어려운 용어 금지.",
  "why_important": "왜 이게 중요한지 1~2문장. 일상생활과 연결해서.",
  "secret_brain_insight": "시크릿 브레인(할 일 관리 시스템) 사용자한테 들려줄 인사이트 문구. 2~3문장. 반말. 감성적으로.",
  "sns_copy": "SNS에 바로 쓸 수 있는 짧은 카피라이팅. 숫자/통계 강조. 이모지 1~2개 포함.",
  "landing_copy": "랜딩페이지에 쓸 신뢰감 있는 문구. 연구 근거 언급. 존댓말.",
  "keywords": ["키워드1", "키워드2", "키워드3"]
}}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text.strip()

        # JSON 파싱
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]

        card_data = json.loads(response_text)

        # 메타데이터 추가
        card = {
            "id": paper.get("paperId", ""),
            "topic": topic,
            "evidence_level": evidence_level,
            "paper_title": title,
            "year": year,
            "citations": citations,
            "authors": [a.get("name", "") for a in (paper.get("authors") or [])[:3]],
            "status": "pending",  # pending → approved / rejected
            "generated_at": datetime.now().isoformat(),
            **card_data
        }

        # 원문 링크
        external_ids = paper.get("externalIds") or {}
        if external_ids.get("DOI"):
            card["doi_url"] = f"https://doi.org/{external_ids['DOI']}"
        if paper.get("openAccessPdf"):
            card["pdf_url"] = paper["openAccessPdf"].get("url", "")

        return card

    except Exception as e:
        print(f"카드 생성 오류 ({title[:30]}): {e}")
        return None


def run_explanation():
    """pending_explanation 상태 논문들 카드 생성"""
    papers_file = "data/papers.json"
    cards_file = "data/cards.json"

    if not os.path.exists(papers_file):
        print("수집된 논문이 없습니다. collector.py를 먼저 실행하세요.")
        return

    with open(papers_file, "r", encoding="utf-8") as f:
        papers = json.load(f)

    # 기존 카드 로드
    existing_cards = []
    if os.path.exists(cards_file):
        with open(cards_file, "r", encoding="utf-8") as f:
            existing_cards = json.load(f)

    existing_card_ids = {c.get("id") for c in existing_cards}

    # 미처리 논문만 필터
    pending = [p for p in papers
               if p.get("status") == "pending_explanation"
               and p.get("paperId") not in existing_card_ids]

    if not pending:
        print("새로 처리할 논문이 없습니다.")
        return

    print(f"🤖 {len(pending)}편 카드 생성 시작...")
    new_cards = []

    for i, paper in enumerate(pending):
        print(f"   [{i+1}/{len(pending)}] {paper.get('title', '')[:50]}...")
        card = generate_card(paper)
        if card:
            new_cards.append(card)
            # 처리 완료 표시
            paper["status"] = "explained"

    # 저장
    os.makedirs("data", exist_ok=True)
    all_cards = existing_cards + new_cards
    with open(cards_file, "w", encoding="utf-8") as f:
        json.dump(all_cards, f, ensure_ascii=False, indent=2)

    with open(papers_file, "w", encoding="utf-8") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {len(new_cards)}개 카드 생성 완료")
    return len(new_cards)


if __name__ == "__main__":
    run_explanation()
