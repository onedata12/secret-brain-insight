"""
자동 스케줄러 - 매일 오전 9시 자동 실행
별도 터미널에서 python scheduler.py 로 실행
"""

import schedule
import time
from datetime import datetime
from collector import run_collection
from explainer import run_explanation


def notify(title: str, message: str):
    try:
        from plyer import notification
        notification.notify(title=title, message=message, app_name="시크릿 브레인", timeout=8)
    except Exception:
        pass


def daily_job():
    print(f"\n{'='*50}")
    print(f"🕘 자동 실행 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}")

    print("\n1단계: 논문 수집")
    try:
        collected = run_collection() or 0
    except Exception as e:
        print(f"수집 오류: {e}")
        collected = 0

    print("\n2단계: 카드 생성")
    try:
        cards_made = run_explanation() or 0
    except Exception as e:
        print(f"카드 생성 오류: {e}")
        cards_made = 0

    print(f"\n{'='*50}")
    print(f"✅ 완료! 논문 {collected}편, 카드 {cards_made}개")
    print(f"대시보드에서 확인하세요: http://localhost:8501")
    print(f"{'='*50}\n")

    if cards_made > 0:
        notify("시크릿 브레인 자동 수집 완료", f"논문 {collected}편, 카드 {cards_made}개가 검토 대기 중이에요!")


# 매일 오전 9시 실행
schedule.every().day.at("09:00").do(daily_job)

print("⏰ 스케줄러 시작됨")
print("   매일 오전 9시에 자동으로 논문을 수집합니다.")
print("   종료하려면 Ctrl+C")
print()

while True:
    schedule.run_pending()
    time.sleep(60)
