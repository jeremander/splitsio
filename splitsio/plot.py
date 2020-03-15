import itertools
import matplotlib
from matplotlib.cm import Dark2
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from splitsio import Run

matplotlib.rcParams.update({
    'axes.labelcolor' : 'red',
    'axes.labelpad' : 8,
})

plt.style.use('ggplot')
COLORS = Dark2.colors


def plot_splits(run: Run) -> None:
    if (run.histories is None):
        raise ValueError('cannot plot splits (no histories)')
    # only plot completed runs
    segment_durations = run.segment_durations(completed = True)
    num_attempts = len(segment_durations)
    max_duration = 0.0
    for (i, tup) in enumerate(segment_durations.itertuples()):
        d = 0.0
        for (color, duration) in zip(itertools.cycle(COLORS), tup[1:]):
            plt.plot([d, d + duration], [i + 1, i + 1], color = color, linewidth = 6)
            d += duration
        max_duration = max(max_duration, d)
    plt.xlim((0.0, max_duration))
    plt.ylim((num_attempts + 0.5, 0.5))
    ax = plt.gca()
    ax.yaxis.set_major_locator(MaxNLocator(integer = True))
    plt.xlabel('time (s)', fontweight = 'bold', color = 'black')
    plt.ylabel('attempt #', fontweight = 'bold', color = 'black')
    runners = ' | '.join(runner.name for runner in run.runners)
    plt.title(f'{run.game.name} {run.category.name}\n{runners}', fontweight = 'bold', fontsize = 14)
    plt.tight_layout()
    plt.show()