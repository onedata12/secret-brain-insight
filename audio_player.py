"""
오디오 플레이어 - edge-tts 기반
카드별 듣기 + 데일리 팟캐스트
배속 조절 지원 (커스텀 HTML 플레이어)
"""

import asyncio
import edge_tts
import os
import streamlit as st
import streamlit.components.v1 as components
import anthropic
from dotenv import load_dotenv

load_dotenv()

AUDIO_DIR = "data/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# 한국어 고품질 음성
VOICE = "ko-KR-SunHiNeural"  # 여성, 자연스러움


async def _generate_tts(text: str, output_path: str):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_path)


def text_to_speech(text: str, filename: str) -> str:
    """텍스트 → MP3 파일 생성, 경로 반환"""
    output_path = os.path.join(AUDIO_DIR, filename)
    if not os.path.exists(output_path):
        asyncio.run(_generate_tts(text, output_path))
    return output_path


def render_audio_player(audio_path: str, title: str = ""):
    """배속 조절 가능한 커스텀 오디오 플레이어"""
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    import base64
    audio_b64 = base64.b64encode(audio_bytes).decode()

    html = f"""
<div style="background:#1e2a3a; border-radius:12px; padding:16px; font-family:'Segoe UI',sans-serif;">
  <div style="color:#a0aec0; font-size:13px; margin-bottom:10px;">🎧 {title}</div>
  <audio id="player" src="data:audio/mp3;base64,{audio_b64}" style="display:none;"></audio>

  <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">

    <!-- 재생/일시정지 -->
    <button onclick="togglePlay()" id="playBtn"
      style="background:#667eea; color:white; border:none; border-radius:8px;
             padding:8px 20px; font-size:14px; cursor:pointer; font-weight:600;">
      ▶ 재생
    </button>

    <!-- 진행바 -->
    <input type="range" id="progress" value="0" min="0" max="100" step="0.1"
      style="flex:1; min-width:100px; accent-color:#667eea; cursor:pointer;"
      oninput="seekAudio(this.value)">

    <!-- 시간 표시 -->
    <span id="timeDisplay" style="color:#718096; font-size:12px; min-width:80px;">0:00 / 0:00</span>

    <!-- 배속 조절 -->
    <div style="display:flex; gap:6px; align-items:center;">
      <span style="color:#718096; font-size:12px;">배속:</span>
      {"".join([f'''
      <button onclick="setSpeed({s})" id="speed{str(s).replace('.','')}"
        style="background:{'#667eea' if s==1.0 else '#2d3748'}; color:white; border:none;
               border-radius:6px; padding:4px 10px; font-size:12px; cursor:pointer;">
        {s}x
      </button>''' for s in [0.8, 1.0, 1.25, 1.5, 2.0]])}
    </div>

  </div>
</div>

<script>
const audio = document.getElementById('player');
const playBtn = document.getElementById('playBtn');
const progress = document.getElementById('progress');
const timeDisplay = document.getElementById('timeDisplay');
let currentSpeed = 1.0;

function togglePlay() {{
  if (audio.paused) {{
    audio.play();
    playBtn.textContent = '⏸ 일시정지';
    playBtn.style.background = '#4a5568';
  }} else {{
    audio.pause();
    playBtn.textContent = '▶ 재생';
    playBtn.style.background = '#667eea';
  }}
}}

function setSpeed(s) {{
  audio.playbackRate = s;
  currentSpeed = s;
  document.querySelectorAll('[id^="speed"]').forEach(btn => {{
    btn.style.background = '#2d3748';
  }});
  document.getElementById('speed' + String(s).replace('.', '')).style.background = '#667eea';
}}

function seekAudio(val) {{
  audio.currentTime = (val / 100) * audio.duration;
}}

function formatTime(sec) {{
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return m + ':' + String(s).padStart(2, '0');
}}

audio.addEventListener('timeupdate', () => {{
  if (audio.duration) {{
    progress.value = (audio.currentTime / audio.duration) * 100;
    timeDisplay.textContent = formatTime(audio.currentTime) + ' / ' + formatTime(audio.duration);
  }}
}});

audio.addEventListener('ended', () => {{
  playBtn.textContent = '▶ 재생';
  playBtn.style.background = '#667eea';
  progress.value = 0;
}});
</script>
"""
    components.html(html, height=120)


def generate_card_audio_script(card: dict) -> str:
    """Claude로 논문 1편 10분짜리 오디오 스크립트 생성"""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = f"""아래 논문을 운동하면서 들을 수 있는 10분짜리 오디오 강의 스크립트로 만들어줘.

조건:
- 반말, 친한 친구 말투
- 마치 팟캐스트 진행자가 혼자 설명하는 느낌
- 중간중간 "있잖아", "근데 신기하지?", "생각해봐" 같은 자연스러운 구어체
- 오디오 전용이니까 마크다운 기호(#, *, -, []) 절대 없이 텍스트만
- 숫자나 통계는 "약 몇 퍼센트", "무려 몇 명" 이런 식으로 강조
- 아래 구성으로:

1. 오프닝 (30초) - 오늘 뭘 배울지 흥미롭게 예고
2. 이 논문이 왜 나왔을까 (1분30초) - 배경 이야기
3. 어떻게 연구했어? (2분) - 방법론을 비유로 쉽게
4. 핵심 발견 (2분) - 결과를 숫자와 함께 임팩트 있게
5. 근데 왜 이게 중요해? (1분30초) - 일상과 연결
6. 시크릿 브레인 사용자에게 (1분30초) - 실생활 적용
7. 마무리 (30초) - 오늘 배운 것 한 줄 정리

논문 정보:
제목: {card.get('paper_title', '')}
핵심: {card.get('one_line', '')}
쉬운 설명: {card.get('easy_explanation', '')}
중요성: {card.get('why_important', '')}
초록: {card.get('abstract_text', '')}
시크릿 브레인 인사이트: {card.get('secret_brain_insight', '')}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def generate_card_audio_text(card: dict) -> str:
    """카드 하나를 오디오용 텍스트로 변환 (짧은 버전 - fallback용)"""
    return f"""
{card.get('headline', '')}

{card.get('easy_explanation', '')}

{card.get('why_important', '')}

시크릿 브레인 인사이트입니다. {card.get('secret_brain_insight', '')}
""".strip()


def generate_daily_podcast_script(cards: list) -> str:
    """승인된 카드들로 데일리 팟캐스트 스크립트 생성"""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    cards_text = ""
    for i, card in enumerate(cards[:5], 1):
        cards_text += f"""
논문 {i}: {card.get('paper_title', '')}
핵심: {card.get('one_line', '')}
설명: {card.get('easy_explanation', '')}
중요성: {card.get('why_important', '')}
시크릿 브레인 인사이트: {card.get('secret_brain_insight', '')}
---"""

    prompt = f"""아래 논문 카드들을 바탕으로 20분 분량의 데일리 팟캐스트 스크립트를 써줘.

조건:
- 친한 친구처럼 반말로 자연스럽게
- 논문 소개 → 핵심 내용 → 실생활 적용 순서
- 논문 사이에 자연스러운 연결 멘트 포함
- 중간중간 "있잖아", "근데", "그래서" 같은 구어체 사용
- 시작: "안녕! 오늘 논문 브리핑 시작할게."
- 끝: "오늘 브리핑 어땠어? 내일도 재밌는 논문 들고 올게!"
- 오디오 전용이니까 마크다운 기호(#, *, -) 없이 텍스트만

논문 카드들:
{cards_text}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def show_card_audio(card: dict):
    """카드 오디오 플레이어 표시 (10분 버전)"""
    card_id = card.get("id", "")[:20]
    audio_file = os.path.join(AUDIO_DIR, f"card_long_{card_id}.mp3")
    script_file = os.path.join(AUDIO_DIR, f"card_long_{card_id}.txt")

    if not os.path.exists(audio_file):
        st.caption("약 40~50초 소요 (스크립트 생성 + 음성 변환)")
        if st.button("🔊 10분 오디오 생성", key=f"audio_gen_{card_id}", type="primary"):
            with st.spinner("스크립트 작성 중... (약 20초)"):
                script = generate_card_audio_script(card)
                with open(script_file, "w", encoding="utf-8") as f:
                    f.write(script)
            with st.spinner("음성 변환 중... (약 20초)"):
                text_to_speech(script, f"card_long_{card_id}.mp3")
            st.rerun()
    else:
        render_audio_player(audio_file, f"📖 {card.get('headline', '')} (~10분)")

        col1, col2 = st.columns(2)
        with col1:
            with open(audio_file, "rb") as f:
                st.download_button(
                    "📥 MP3 저장",
                    f,
                    file_name=f"{card.get('headline', 'audio')[:20]}.mp3",
                    mime="audio/mp3",
                    use_container_width=True,
                    key=f"dl_{card_id}"
                )
        with col2:
            if st.button("🔄 재생성", key=f"regen_{card_id}", use_container_width=True):
                os.remove(audio_file)
                if os.path.exists(script_file):
                    os.remove(script_file)
                st.rerun()

        if os.path.exists(script_file):
            with st.expander("📝 스크립트 보기"):
                with open(script_file, "r", encoding="utf-8") as f:
                    st.markdown(f.read())


def show_daily_podcast(cards: list):
    """데일리 팟캐스트 UI"""
    from datetime import datetime
    today = datetime.now().strftime("%Y%m%d")
    script_file = os.path.join(AUDIO_DIR, f"podcast_{today}.txt")
    audio_file = os.path.join(AUDIO_DIR, f"podcast_{today}.mp3")

    approved = [c for c in cards if c.get("status") == "approved"]
    if not approved:
        st.info("승인된 카드가 없어요. 먼저 카드를 승인해주세요.")
        return

    st.caption(f"승인된 카드 {len(approved)}개 기반 | 예상 재생시간 약 {min(len(approved)*4, 20)}분")

    if not os.path.exists(audio_file):
        if st.button("🎙️ 오늘의 팟캐스트 생성", type="primary", use_container_width=True):
            with st.spinner("스크립트 작성 중... (약 20초)"):
                script = generate_daily_podcast_script(approved)
                with open(script_file, "w", encoding="utf-8") as f:
                    f.write(script)

            with st.spinner("음성 생성 중... (약 30초)"):
                text_to_speech(script, f"podcast_{today}.mp3")
            st.success("팟캐스트 생성 완료!")
            st.rerun()

        # 스크립트만 미리 보기
        if os.path.exists(script_file):
            with st.expander("📝 스크립트 미리보기"):
                with open(script_file, "r", encoding="utf-8") as f:
                    st.text(f.read())
    else:
        render_audio_player(audio_file, f"오늘의 논문 브리핑 ({datetime.now().strftime('%m월 %d일')})")

        col1, col2 = st.columns(2)
        with col1:
            with open(audio_file, "rb") as f:
                st.download_button(
                    "📥 MP3 다운로드 (핸드폰 저장)",
                    f,
                    file_name=f"논문브리핑_{today}.mp3",
                    mime="audio/mp3",
                    use_container_width=True
                )
        with col2:
            if st.button("🔄 새로 생성", use_container_width=True):
                os.remove(audio_file)
                if os.path.exists(script_file):
                    os.remove(script_file)
                st.rerun()

        if os.path.exists(script_file):
            with st.expander("📝 스크립트 보기"):
                with open(script_file, "r", encoding="utf-8") as f:
                    st.markdown(f.read())
