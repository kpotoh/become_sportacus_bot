from __future__ import annotations

import io
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import MaxNLocator

# Distinct colors/markers so overlapping 0/1 series stay readable
_STYLES = [
    ("#2a9d8f", "o", "-"),
    ("#e76f51", "s", "-"),
    ("#264653", "^", "--"),
    ("#e9c46a", "D", "-"),
    ("#9b5de5", "v", "--"),
    ("#00bbf9", "P", "-"),
    ("#f15bb5", "X", "--"),
    ("#00f5d4", "h", "-"),
]


def chart_week_workouts(
    series: dict[str, list[int]],
    days: list[date],
    title: str = "Тренировки за 7 дней",
) -> bytes:
    """
    One line per workout. X = last 7 days, Y = 1 if done that day else 0.
    """
    fig, ax = plt.subplots(figsize=(10, 4.5))
    labels = [d.strftime("%a\n%d.%m") for d in days]
    x = list(range(len(days)))

    if not series:
        ax.text(0.5, 0.5, "Нет данных", ha="center", va="center", transform=ax.transAxes)
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
    else:
        for i, (name, values) in enumerate(series.items()):
            color, marker, ls = _STYLES[i % len(_STYLES)]
            # Tiny vertical offset so coincident points remain distinguishable
            offset = (i - (len(series) - 1) / 2) * 0.04
            ys = [v + offset for v in values]
            ax.plot(
                x,
                ys,
                color=color,
                marker=marker,
                linestyle=ls,
                linewidth=2,
                markersize=8,
                label=name,
            )

        ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
        ax.set_ylim(-0.15, 1.2)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["нет", "да"])

    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlabel("День")
    ax.set_ylabel("Выполнено")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140)
    plt.close(fig)
    buf.seek(0)
    return buf.read()
