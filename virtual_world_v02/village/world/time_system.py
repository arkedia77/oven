"""시간 압축 시스템 — 1시간 실시간 = 마을 1일"""

TIME_PERIODS = [
    ("early_morning", 6, 8),    # 기상
    ("morning", 8, 12),         # 업무
    ("lunch", 12, 14),          # 점심
    ("afternoon", 14, 18),      # 오후
    ("evening", 18, 21),        # 저녁
    ("night", 21, 23),          # 야간
    ("late_night", 23, 6),      # 수면
]


def village_hour_to_period(hour: int) -> str:
    for period, start, end in TIME_PERIODS:
        if start <= end:
            if start <= hour < end:
                return period
        else:
            if hour >= start or hour < end:
                return period
    return "late_night"


def format_village_time(hour: int) -> str:
    period_names = {
        "early_morning": "이른 아침",
        "morning": "오전",
        "lunch": "점심",
        "afternoon": "오후",
        "evening": "저녁",
        "night": "밤",
        "late_night": "심야",
    }
    period = village_hour_to_period(hour)
    return f"{hour:02d}:00 ({period_names[period]})"
