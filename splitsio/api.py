"""Python implementation of the splits.io REST API.
See https://github.com/glacials/splits-io/blob/master/docs/api.md for schema details."""

from dataclasses import dataclass, Field, field
from datetime import datetime
import dateutil.parser
import numpy as np
import pandas as pd
from operator import attrgetter
from typing import Any, cast, Counter, List, NamedTuple, Optional, Sequence, Type

from dataclasses_json import config
from marshmallow import fields

from splitsio.query import SplitsIOData


CategoryCounts = NamedTuple('CategoryCounts', [('category', 'Category'), ('numRuns', int)])


############
# DATETIME #
############

class IsoDatetime(datetime):
    """Custom datetime class with ISO formatting."""
    @classmethod
    def isoparse(cls, timestamp: str) -> 'IsoDatetime':
        s = timestamp.strip("'").rstrip('Z')
        dt = dateutil.parser.isoparse(s)
        return datetime.__new__(cls, dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond, dt.tzinfo)  # type: ignore
    def __repr__(self) -> str:
        return repr(str(self))
    def __str__(self) -> str:
        return self.isoformat(timespec = 'milliseconds') + 'Z'

isoparse = lambda ts : None if (ts is None) else IsoDatetime.isoparse(ts)

isoformat = lambda dt : None if (dt is None) else str(dt)

def isodatetime(**kwargs: Any) -> Field:  # type: ignore
    """dataclass field rendering a datetime object as a string when parsing/formatting."""
    return field(metadata = config(encoder = isoformat, decoder = isoparse, mm_field = fields.DateTime(format = 'iso')), **kwargs)


##############
# DATA MODEL #
##############

@dataclass
class Category(SplitsIOData):
    """A Category is a ruleset for a Game (Any%, 100%, MST, etc.) and an optional container for Runs. Its canonical ID string is a base 10 number, e.g. "312", "1456", "11"."""
    id: str
    name: str
    created_at: Optional[datetime] = isodatetime(default = None, repr = False)
    updated_at: Optional[datetime] = isodatetime(default = None, repr = False)
    @classmethod
    def collection(cls) -> str:
        return "categories"
    @property
    def canonical_id(self) -> str:
        return self.id
    def runs(self) -> Sequence['Run']:
        """Runs for the category."""
        return self.get_associated(Run)
    def runners(self) -> Sequence['Runner']:
        """Runners for the category."""
        return self.get_associated(Runner)

@dataclass
class Game(SplitsIOData):
    """A Game is a collection of information about a game, and a container for Categories. Its canonical ID string is its Speedrun.com shortname, e.g. "sms", "sm64", "portal"."""
    id: str
    name: str
    shortname: Optional[str]
    created_at: Optional[datetime] = isodatetime(default = None, repr = False)
    updated_at: Optional[datetime] = isodatetime(default = None, repr = False)
    categories: Optional[List[Category]] = field(default = None, repr = False)
    @classmethod
    def collection(cls) -> str:
        return "games"
    @property
    def canonical_id(self) -> str:
        return self.name if (self.shortname is None) else self.shortname
    @classmethod
    def all(cls) -> Sequence['Game']:
        """Obtains the list of all games."""
        return cls.query(cls.collection())
    @classmethod
    def search(cls, name: str) -> Sequence['Game']:
        """Obtains the list of games matching a given search term."""
        return cls.query(cls.collection() + '?search=' + name)
    def runs(self) -> Sequence['Run']:
        """Runs for the game."""
        return self.get_associated(Run)
    def runners(self) -> Sequence['Runner']:
        """Runners for the game."""
        return self.get_associated(Runner)
    def category_counts(self) -> List[CategoryCounts]:
        """Returns categories along with number of runs for that category."""
        if (self.categories is None):
            return []
        run_ctr: Counter[str] = Counter()
        for run in self.runs():
            if run.category:
                run_ctr[run.category.id] += 1
        items = [CategoryCounts(cat, run_ctr[cat.id]) for cat in self.categories]
        # sort by decreasing number of runs
        items.sort(key = attrgetter('numRuns'), reverse = True)
        return items


@dataclass
class Runner(SplitsIOData):
    """A Runner is a user who has at least one run tied to their account. Its canonical ID string is their Splits.io username all-lowercased, e.g. "glacials", "batedurgonnadie", "snarfybobo"."""
    id: str
    twitch_id: Optional[str]
    twitch_name: Optional[str]
    display_name: str
    name: str
    avatar: Optional[str] = field(default = None, repr = False)
    created_at: Optional[datetime] = isodatetime(default = None, repr = False)
    updated_at: Optional[datetime] = isodatetime(default = None, repr = False)
    @classmethod
    def collection(cls) -> str:
        return "runners"
    @property
    def canonical_id(self) -> str:
        return self.name.lower()
    def runs(self) -> Sequence['Run']:
        """The runner's runs."""
        return self.get_associated(Run)
    def pbs(self) -> Sequence['Run']:
        """The runner's personal best runs."""
        return self.get_associated(Run, 'pbs')
    def games(self) -> Sequence[Game]:
        """Games for which the runner has at least one speedrun."""
        return self.get_associated(Game)
    def categories(self) -> Sequence[Category]:
        """Categories the runner has participated in."""
        return self.get_associated(Category)

@dataclass
class History(SplitsIOData):
    """History of a split on some previous run."""
    attempt_number: int
    realtime_duration_ms: Optional[int]
    gametime_duration_ms: Optional[int]
    started_at: Optional[datetime] = isodatetime(default = None)
    ended_at: Optional[datetime] = isodatetime(default = None)
    @classmethod
    def collection(cls) -> str:
        return "histories"
    @property
    def canonical_id(self) -> str:
        raise NotImplementedError
    def is_complete(self) -> bool:
        """Returns True if the run is complete (not reset).
        It is considered complete if it has a stored realtime or gametime duration."""
        return (self.realtime_duration_ms is not None) or (self.gametime_duration_ms is not None)
    def duration(self) -> Optional[float]:
        """Gets the duration in milliseconds. First tries realtime, then gametime, then elapsed time between start and end timestamps."""
        dur = getattr(self, 'realtime_duration_ms', getattr(self, 'gametime_duration_ms', None))
        if (dur is None):
            start = self.started_at
            end = self.ended_at
            if (start is not None) and (end is not None):
                dur = (end - start).seconds * 1000
        return dur

@dataclass
class Segment(SplitsIOData):
    """A Segment maps to a single piece of a run, also called a split. Its canonical ID string is a UUID, e.g. "c198a25f-9f8a-43cd-92ab-472a952f9336"."""
    id: str
    name: str
    display_name: str
    segment_number: int
    realtime_start_ms: int
    realtime_duration_ms: int
    realtime_end_ms: int
    realtime_shortest_duration_ms: Optional[int]
    realtime_gold: bool
    realtime_skipped: bool
    realtime_reduced: bool
    gametime_start_ms: int
    gametime_duration_ms: int
    gametime_end_ms: int
    gametime_shortest_duration_ms: Optional[int]
    gametime_gold: bool
    gametime_skipped: bool
    gametime_reduced: bool
    histories: Optional[List[History]] = field(default = None, repr = False)
    @classmethod
    def collection(cls) -> str:
        return "segments"
    @property
    def canonical_id(self) -> str:
        return self.id

@dataclass
class Run(SplitsIOData):
    """A Run maps 1:1 to an uploaded splits file. Its canonical ID string is a base 36 number, e.g. "1b" "3nm" "1vr"."""
    id: str
    srdc_id: Optional[str]
    realtime_duration_ms: int
    realtime_sum_of_best_ms: Optional[int]
    gametime_duration_ms: int
    gametime_sum_of_best_ms: Optional[int]
    default_timing: str
    program: str
    attempts: Optional[int]
    image_url: Optional[int]
    parsed_at: datetime = isodatetime()
    created_at: datetime = isodatetime()
    updated_at: datetime = isodatetime()
    video_url: Optional[str] = None
    game: Optional[Game] = None
    category: Optional[Category] = None
    runners: List[Runner] = field(default_factory = lambda : [])
    segments: Optional[List[Segment]] = field(default = None, repr = False)
    histories: Optional[List[History]] = field(default = None, repr = False)
    @classmethod
    def collection(cls) -> str:
        return "runs"
    @property
    def canonical_id(self) -> str:
        return self.id
    @classmethod
    def from_id(cls: Type['Run'], id_: str, historic: bool = False, **params: Any) -> 'Run':
        """If historic = True, additionally retrieves all historic run data."""
        params['historic'] = 1 if historic else 0
        run = super(Run, cls).from_id(id_, **params)
        if run.histories:  # sort chronologically ascending
            run.histories = run.histories[::-1]
        return run
    @property
    def completed_attempts(self) -> List[History]:
        """Returns all completed run attempts.
        A completed attempt is one whose last segment has been completed."""
        segments = [] if (self.segments is None) else self.segments
        if (self.histories is None) or (len(segments) == 0):
            return []
        completed_attempt_numbers = {history.attempt_number for history in segments[-1].histories}  # type: ignore
        return [history for history in self.histories if (history.attempt_number in completed_attempt_numbers)]
    def segment_durations(self, complete: bool = True, clean: bool = False) -> pd.DataFrame:
        """Returns a table of segment durations, in seconds.
        Rows are attempts (in chronological order); columns are segments.
        If complete = True, only includes completed attempts.
        If clean = True, only includes attempts where each segment is completed (i.e. no missing splits).
        Missing splits are assigned zero duration."""
        if (self.histories is None):
            raise ValueError("cannot get segment durations without run histories")
        segments = [] if (self.segments is None) else self.segments
        if complete and (len(segments) > 0):
            attempt_numbers = [h.attempt_number for h in self.histories if h.is_complete()]
        else:
            attempt_numbers = [h.attempt_number for h in self.histories]
        attempt_number_indices = {j : i for (i, j) in enumerate(attempt_numbers)}
        arr = np.zeros((len(attempt_number_indices), len(segments)), dtype = float)
        arr[:] = np.nan
        # fill in segment durations
        for (j, seg) in enumerate(segments):
            for h in seg.histories:  # type: ignore
                attempt_number = h.attempt_number
                if (attempt_number in attempt_number_indices):
                    arr[attempt_number_indices[attempt_number], j] = h.duration() / 1000  # type: ignore
        df = pd.DataFrame(arr, index = pd.Index(attempt_numbers, name = 'attempt'), columns =  [seg.name for seg in segments])
        if clean:  # zero values are invalid
            return df.replace(0.0, np.nan).dropna(axis = 0, how = 'any')
        return df.dropna(axis = 0, how = 'all').fillna(0.0)
    def split_durations(self, complete: bool = True, clean: bool = False) -> pd.DataFrame:
        """Returns a table of split durations (cumulative segment durations), in seconds.
        Rows are attempts (in chronological order); columns are splits."""
        seg_durs = self.segment_durations(complete, clean)
        split_durs = seg_durs.cumsum(axis = 1)
        split_durs['total'] = split_durs[split_durs.columns[-1]]
        histories = cast(List[History], self.histories)
        attempt_number_indices = {h.attempt_number : i for (i, h) in enumerate(histories)}
        true_totals = []
        for j in split_durs.index:
            history = histories[attempt_number_indices[j]]
            dur = history.duration()
            true_totals.append(None if (dur is None) else (dur / 1000))
        split_durs['true_total'] = true_totals
        return split_durs
