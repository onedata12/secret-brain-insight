"""
논문 수집기 - Semantic Scholar API
메타분석/체계적문헌고찰 우선 필터링
"""

import requests
import json
import os
import time
from datetime import datetime

SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

# 메타분석/SR 관련 키워드
META_KEYWORDS = [
    "meta-analysis", "systematic review", "meta analysis",
    "randomized controlled trial", "RCT", "cochrane"
]

def search_papers(topic: str, max_results: int = 20) -> list:
    """주제로 논문 검색 (메타분석 우선)"""

    # 메타분석 필터 포함한 검색어 (중복 방지)
    if "meta-analysis" in topic.lower() or "systematic review" in topic.lower():
        query = topic
    else:
        query = f"{topic} meta-analysis OR systematic review"

    params = {
        "query": query,
        "limit": max_results,
        "fields": "title,abstract,year,authors,citationCount,externalIds,openAccessPdf,publicationTypes"
    }

    try:
        time.sleep(2)  # Rate limit 방지
        response = requests.get(SEMANTIC_SCHOLAR_URL, params=params, timeout=10)
        if response.status_code == 429:
            print("   Rate limit - 10초 대기 후 재시도...")
            time.sleep(10)
            response = requests.get(SEMANTIC_SCHOLAR_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        papers = data.get("data", [])

        # 신뢰도 점수 계산 및 정렬
        scored_papers = []
        for paper in papers:
            if not paper.get("abstract"):
                continue

            score = calculate_trust_score(paper)
            paper["trust_score"] = score
            paper["search_topic"] = topic
            scored_papers.append(paper)

        # 신뢰도 높은 순으로 정렬
        scored_papers.sort(key=lambda x: x["trust_score"], reverse=True)
        return scored_papers[:10]

    except Exception as e:
        print(f"검색 오류: {e}")
        return []


def calculate_trust_score(paper: dict) -> int:
    """논문 신뢰도 점수 계산"""
    score = 0

    title = (paper.get("title") or "").lower()
    abstract = (paper.get("abstract") or "").lower()
    pub_types = paper.get("publicationTypes") or []

    # 논문 타입 점수
    if "Meta-Analysis" in pub_types:
        score += 50
    if "SystematicReview" in pub_types:
        score += 40
    if "Review" in pub_types:
        score += 20
    if "RCT" in pub_types or "ClinicalTrial" in pub_types:
        score += 30

    # 제목/초록 키워드 점수
    for kw in META_KEYWORDS:
        if kw.lower() in title:
            score += 15
        if kw.lower() in abstract:
            score += 5

    # 인용 수 점수 (최대 20점)
    citations = paper.get("citationCount") or 0
    score += min(citations // 10, 20)

    # 최신성 점수
    year = paper.get("year") or 0
    if year >= 2020:
        score += 10
    elif year >= 2015:
        score += 5

    return score


def get_evidence_level(paper: dict) -> str:
    """근거 수준 라벨"""
    pub_types = paper.get("publicationTypes") or []
    title = (paper.get("title") or "").lower()
    abstract = (paper.get("abstract") or "").lower()

    if "Meta-Analysis" in pub_types or "meta-analysis" in title:
        return "🥇 메타분석"
    elif "SystematicReview" in pub_types or "systematic review" in title:
        return "🥈 체계적 문헌고찰"
    elif "Review" in pub_types or "review" in title:
        return "🥉 리뷰 논문"
    elif "RCT" in pub_types or "randomized" in abstract:
        return "🔬 무작위 대조 시험"
    else:
        return "📄 일반 논문"


def load_topics() -> list:
    """topics.json에서 주제 목록 로드"""
    topics_file = "data/topics.json"
    if os.path.exists(topics_file):
        with open(topics_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_papers(new_papers: list):
    """수집된 논문을 papers.json에 저장 (중복 제거)"""
    os.makedirs("data", exist_ok=True)
    papers_file = "data/papers.json"

    existing = []
    if os.path.exists(papers_file):
        with open(papers_file, "r", encoding="utf-8") as f:
            existing = json.load(f)

    # 기존 paper ID 목록
    existing_ids = {p.get("paperId") for p in existing}

    added = 0
    for paper in new_papers:
        if paper.get("paperId") not in existing_ids:
            paper["collected_at"] = datetime.now().isoformat()
            paper["evidence_level"] = get_evidence_level(paper)
            paper["status"] = "pending_explanation"
            paper["abstract_text"] = paper.get("abstract", "")  # 원문 리더용
            existing.append(paper)
            existing_ids.add(paper.get("paperId"))
            added += 1

    with open(papers_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    return added


def run_collection():
    """전체 주제 수집 실행"""
    topics = load_topics()
    if not topics:
        print("주제가 없습니다. 앱에서 먼저 주제를 추가하세요.")
        return

    total_added = 0
    for topic_obj in topics:
        topic_name = topic_obj.get("name", "")
        query = topic_obj.get("query", topic_name)
        print(f"🔍 수집 중: {topic_name}")

        papers = search_papers(query)
        added = save_papers(papers)
        total_added += added
        print(f"   → {len(papers)}편 검색, {added}편 신규 저장")

    print(f"\n✅ 총 {total_added}편 신규 논문 수집 완료")
    return total_added


if __name__ == "__main__":
    run_collection()
