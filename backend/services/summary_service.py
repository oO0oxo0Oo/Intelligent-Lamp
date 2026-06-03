from datetime import datetime


def build_summary(session, warning_count, leave_count):
    started_at = session.get("started_at")
    ended_at = session.get("ended_at")
    duration_seconds = session.get("duration_seconds", 0)

    if started_at:
        started_text = datetime.fromtimestamp(started_at).strftime("%H:%M:%S")
    else:
        started_text = "--"

    if ended_at:
        ended_text = datetime.fromtimestamp(ended_at).strftime("%H:%M:%S")
    else:
        ended_text = "--"

    minutes = duration_seconds // 60
    seconds = duration_seconds % 60
    return (
        f"本次学习开始于 {started_text}，结束于 {ended_text}，"
        f"累计学习 {minutes} 分 {seconds} 秒，"
        f"离桌 {leave_count} 次，异常提醒 {warning_count} 次。"
    )

