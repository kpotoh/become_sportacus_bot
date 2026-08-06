from __future__ import annotations

import io
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def chart_daily_counts(day_counts: dict[date, int], title: str) -> bytes:
    if not day_counts:
        # empty chart
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.set_title(title)
        ax.text(0.5, 0.5, "Нет данных", ha="center", va="center", transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
    else:
        days = sorted(day_counts.keys())
        values = [day_counts[d] for d in days]
        labels = [d.strftime("%d.%m") for d in days]
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(labels, values, color="#2a9d8f")
        ax.set_title(title)
        ax.set_ylabel("Тренировок")
        ax.tick_params(axis="x", rotation=45)
        fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def chart_monthly_counts(month_counts: dict[str, int], title: str) -> bytes:
    if not month_counts:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.set_title(title)
        ax.text(0.5, 0.5, "Нет данных", ha="center", va="center", transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
    else:
        months = sorted(month_counts.keys())
        values = [month_counts[m] for m in months]
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(months, values, color="#e76f51")
        ax.set_title(title)
        ax.set_ylabel("Тренировок")
        ax.tick_params(axis="x", rotation=45)
        fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140)
    plt.close(fig)
    buf.seek(0)
    return buf.read()
