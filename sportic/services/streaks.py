from __future__ import annotations

from sportic.texts import is_milestone, milestone_message


def compute_new_streak(previous: int, *, reset: bool = False) -> int:
    if reset:
        return 0
    return previous + 1


def celebration_extra(streak: int) -> str:
    if is_milestone(streak):
        msg = milestone_message(streak)
        return f"\n\n🔥 {msg}" if msg else ""
    return ""
