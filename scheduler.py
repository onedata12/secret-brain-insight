"""
자동 스케줄러 - 매주 월요일 오전 9시 자동 실행
별도 터미널에서 python scheduler.py 로 실행
"""

import schedule
import time
from datetime import datetime
from collector import run_collection
from explainer import run_explanation


def weekly_job():
    print(f"\n{'='*50}")
    print(f"🕘 자동 실행 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}")

    print("\n1단계: 논문 수집")
    collected = run_collection()

    print("\n2단계: 카드 생성")
    cards_made = run_explanation()

    print(f"\n{'='*50}")
    print(f"✅ 완료! 논문 {collected}편, 카드 {cards_made}개")
    print(f"대시보드에서 확인하세요: http://localhost:8501")
    print(f"{'='*50}\n")


# 매주 월요일 오전 9시 실행
schedule.every().monday.at("09:00").do(weekly_job)

print("⏰ 스케줄러 시작됨")
print("   매주 월요일 오전 9시에 자동으로 논문을 수집합니다.")
print("   종료하려면 Ctrl+C")
print()

# 즉시 한 번 실행할지 확인
run_now = input("지금 바로 한 번 실행할까요? (y/n): ").strip().lower()
if run_now == "y":
    weekly_job()

while True:
    schedule.run_pending()
    time.sleep(60)
