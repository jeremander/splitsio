import itertools
from matplotlib.cm import Dark2
import matplotlib.pyplot as plt
from typing import DefaultDict, List

from model import Run

COLORS = Dark2.colors


def plot_splits(run: Run) -> None:
    if (run.histories is None):
        raise ValueError('cannot plot splits (no histories)')
    attempt_numbers = set([h.attempt_number for h in run.segments[-1].histories])
    # attempt_numbers = sorted(set([h.attempt_number for seg in run.segments for h in seg.histories]))
    num_attempts = len(attempt_numbers)
    durations_by_attempt: DefaultDict[int, List[float]] = DefaultDict(list)
    for seg in run.segments:
        for h in seg.histories:
            attempt = h.attempt_number
            if (attempt in attempt_numbers):
                durations_by_attempt[h.attempt_number].append(h.realtime_duration_ms / 1000)
    max_duration = 0.0
    for (i, attempt) in enumerate(sorted(attempt_numbers)):
        d = 0.0
        for (color, duration) in zip(itertools.cycle(COLORS), durations_by_attempt[attempt]):
            plt.plot([d, d + duration], [i + 1, i + 1], color = color, linewidth = 4)
            d += duration
        max_duration = max(max_duration, d)
    plt.xlim((0.0, max_duration))
    plt.ylim((0.5, num_attempts + 0.5))
    plt.xlabel('time (s)', fontweight = 'bold')
    plt.ylabel('attempt #', fontweight = 'bold')
    runners = ' | '.join(runner.name for runner in run.runners)
    plt.title(f'{run.game.name} {run.category.name}\n{runners}', fontweight = 'bold', fontsize = 14)
    plt.show()