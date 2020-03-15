"""Functions for producing various plots based on speedrun data.
Much of this is a work-in-progress.
For official in-browser graphs, use splits.io Gold features."""

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import time

from splitsio import Run

plt.style.use('ggplot')


def plot_splits(run: Run, complete: bool = True, clean: bool = False) -> None:
    """Plots split durations for all completed attempts as a stacked bar plot.
    If complete = True, only includes completed attempts.
    If clean = True, only includes attempts where each segment is completed (i.e. no missing splits).
    Missing splits are assigned zero duration."""
    if (run.histories is None):
        raise ValueError('cannot plot splits (no histories)')
    seg_durs = run.segment_durations(complete = complete, clean = clean)
    cum_seg_durs = seg_durs.cumsum(axis = 1)
    max_duration = cum_seg_durs.max().max()
    y = np.arange(len(seg_durs))
    left = None
    for col in seg_durs.columns:
        plt.barh(y, seg_durs[col], height = 0.75, left = left)
        left = cum_seg_durs[col]
    plt.xlim((0.0, max_duration * 1.3))
    plt.ylim((max(y) + 0.5, -0.5))
    plt.legend(seg_durs.columns)
    ax = plt.gca()
    xformatter = FuncFormatter(lambda s, x: time.strftime('%M:%S', time.gmtime(s)))
    ax.xaxis.set_major_formatter(xformatter)
    def get_attempt_number(i: int, y: float) -> str:
        try:
            return str(seg_durs.index[i])
        except IndexError:
            return ''
    yformatter = FuncFormatter(get_attempt_number)
    ax.yaxis.set_major_formatter(yformatter)
    plt.xlabel('time (MM:SS)', fontweight = 'bold', color = 'black')
    plt.ylabel('attempt #', fontweight = 'bold', color = 'black')
    runners = ' | '.join(runner.name for runner in run.runners)
    plt.title(f'{run.game.name} {run.category.name}\n{runners}', fontweight = 'bold', fontsize = 14)  # type: ignore
    plt.tight_layout()
    plt.show()