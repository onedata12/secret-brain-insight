"""
논문 원문 리더 - 좌우 분할 + 호버 하이라이트
왼쪽: 영어 원문 (문장 단위)
오른쪽: 한국어 번역 (문장 단위)
호버 시 대응 문장 하이라이트
"""

import streamlit.components.v1 as components
import anthropic
import os
import json
from dotenv import load_dotenv

load_dotenv()


def translate_sentences(text: str) -> list[dict]:
    """영어 텍스트를 문장 단위로 분리하고 번역"""
    import re
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # 긴 텍스트는 앞 2000자만 사용 (JSON 잘림 방지)
    if len(text) > 2000:
        text = text[:2000] + "..."

    prompt = f"""아래 영어 텍스트를 문장 단위로 분리하고, 각 문장을 자연스러운 한국어로 번역해줘.

반드시 아래 JSON 형식으로만 응답해. 다른 텍스트 없이 JSON 배열만:

[
  {{"id": 1, "en": "영어 원문 문장", "ko": "한국어 번역 문장"}},
  {{"id": 2, "en": "영어 원문 문장", "ko": "한국어 번역 문장"}}
]

번역할 텍스트:
{text}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    response = message.content[0].text.strip()

    # 코드블록 제거
    if "```" in response:
        parts = response.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("["):
                response = part
                break

    # JSON 배열 부분만 추출
    match = re.search(r'\[.*\]', response, re.DOTALL)
    if match:
        response = match.group(0)

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # 마지막 불완전한 항목 제거 후 재시도
        last_complete = response.rfind('},')
        if last_complete > 0:
            response = response[:last_complete+1] + ']'
            try:
                return json.loads(response)
            except:
                pass
        # 완전히 실패하면 문장 단순 분리 후 반환
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        return [{"id": i+1, "en": s, "ko": "(번역 실패 - 다시 시도해주세요)"} for i, s in enumerate(sentences)]


def render_parallel_reader(sentences: list[dict], paper_title: str = ""):
    """좌우 분할 + 호버 하이라이트 HTML 렌더링"""

    left_items = ""
    right_items = ""

    for s in sentences:
        sid = s["id"]
        en = s["en"].replace("'", "\\'").replace('"', '&quot;')
        ko = s["ko"].replace("'", "\\'").replace('"', '&quot;')

        left_items += f'''
        <div class="sentence" id="en-{sid}"
             onmouseover="highlight({sid})"
             onmouseout="unhighlight({sid})">
          <span class="sent-num">{sid}</span>
          {s["en"]}
        </div>'''

        right_items += f'''
        <div class="sentence" id="ko-{sid}"
             onmouseover="highlight({sid})"
             onmouseout="unhighlight({sid})">
          <span class="sent-num">{sid}</span>
          {s["ko"]}
        </div>'''

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', sans-serif; background: #0e1117; color: #fafafa; }}

  .title {{
    padding: 16px 20px;
    font-size: 15px;
    font-weight: 600;
    color: #a0aec0;
    border-bottom: 1px solid #2d3748;
  }}

  .container {{
    display: flex;
    height: calc(100vh - 56px);
  }}

  .panel {{
    flex: 1;
    overflow-y: auto;
    padding: 16px;
  }}

  .panel-left {{
    border-right: 1px solid #2d3748;
  }}

  .panel-header {{
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
    color: #718096;
    padding: 0 0 12px 0;
    text-transform: uppercase;
  }}

  .sentence {{
    padding: 10px 12px;
    margin: 4px 0;
    border-radius: 6px;
    border-left: 3px solid transparent;
    cursor: default;
    line-height: 1.7;
    font-size: 14px;
    transition: all 0.15s ease;
    color: #e2e8f0;
  }}

  .sentence:hover {{
    background: #1a2035;
    border-left-color: #667eea;
  }}

  .sentence.highlighted {{
    background: #1e2a4a;
    border-left-color: #667eea;
    color: #ffffff;
  }}

  .sent-num {{
    display: inline-block;
    width: 22px;
    height: 22px;
    line-height: 22px;
    text-align: center;
    border-radius: 50%;
    background: #2d3748;
    color: #718096;
    font-size: 11px;
    font-weight: 700;
    margin-right: 8px;
    flex-shrink: 0;
  }}

  .sentence.highlighted .sent-num {{
    background: #667eea;
    color: white;
  }}

  /* 스크롤바 */
  .panel::-webkit-scrollbar {{ width: 6px; }}
  .panel::-webkit-scrollbar-track {{ background: #1a202c; }}
  .panel::-webkit-scrollbar-thumb {{ background: #4a5568; border-radius: 3px; }}
</style>
</head>
<body>

<div class="title">📄 {paper_title}</div>

<div class="container">
  <div class="panel panel-left">
    <div class="panel-header">🇺🇸 원문 (English)</div>
    {left_items}
  </div>
  <div class="panel panel-right">
    <div class="panel-header">🇰🇷 번역 (한국어)</div>
    {right_items}
  </div>
</div>

<script>
function highlight(id) {{
  document.getElementById('en-' + id).classList.add('highlighted');
  document.getElementById('ko-' + id).classList.add('highlighted');

  // 번역 패널에서 해당 문장이 보이도록 스크롤
  const koEl = document.getElementById('ko-' + id);
  const panel = document.querySelector('.panel-right');
  const panelRect = panel.getBoundingClientRect();
  const elRect = koEl.getBoundingClientRect();
  if (elRect.top < panelRect.top || elRect.bottom > panelRect.bottom) {{
    koEl.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
  }}
}}

function unhighlight(id) {{
  document.getElementById('en-' + id).classList.remove('highlighted');
  document.getElementById('ko-' + id).classList.remove('highlighted');
}}
</script>
</body>
</html>
"""
    return html


def show_paper_reader(paper: dict):
    """논문 리더 페이지 표시"""
    import streamlit as st

    title = paper.get("paper_title", "")
    abstract = paper.get("abstract_text", "")

    if not abstract:
        st.warning("이 논문은 원문 초록이 저장되어 있지 않아요.")
        st.info("논문을 다시 수집하면 초록이 포함됩니다.")
        return

    cache_key = f"sentences_{paper.get('id', '')}"

    if cache_key not in st.session_state:
        with st.spinner("번역 중... (약 10초)"):
            try:
                sentences = translate_sentences(abstract)
                st.session_state[cache_key] = sentences
            except Exception as e:
                st.error(f"번역 오류: {e}")
                return

    sentences = st.session_state[cache_key]
    html = render_parallel_reader(sentences, title)
    components.html(html, height=600, scrolling=False)
