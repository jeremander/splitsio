"""Python implementation of the splits.io REST API.
See https://github.com/glacials/splits-io/blob/master/docs/api.md for schema details."""

from abc import abstractproperty
from dataclasses import dataclass, Field, field
from datetime import datetime
import dateutil.parser
from operator import attrgetter
import requests
from typing import Any, Counter, Dict, List, NamedTuple, Optional, Type, TypeVar

from dataclasses_json import config, DataClassJsonMixin
from marshmallow import fields


#####################
# TYPES & CONSTANTS #
#####################

API_URL = 'https://splits.io/api/v4/'
USER_AGENT = 'splitsio_api'

T = TypeVar('T', bound = 'SplitsIOData')
Url = str
JSONDict = Dict[str, Any]
CategoryCounts = NamedTuple('CategoryCounts', [('category', 'Category'), ('numRuns', int)])


############
# DATETIME #
############

class IsoDatetime(datetime):
    """Custom datetime class with ISO formatting."""
    @classmethod
    def isoparse(cls, timestamp: str) -> 'IsoDatetime':
        dt = dateutil.parser.isoparse(timestamp.rstrip('Z'))
        return datetime.__new__(cls, dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond, dt.tzinfo)
    def __repr__(self) -> str:
        return self.isoformat(timespec = 'milliseconds') + 'Z'

isoparse = lambda ts : None if (ts is None) else IsoDatetime.isoparse(ts)

isoformat = lambda dt : None if (dt is None) else repr(dt)

def isodatetime(**kwargs: Any) -> Field:
    """dataclass field rendering a datetime object as a string when parsing/formatting."""
    return field(metadata = config(encoder = isoformat, decoder = isoparse, mm_field = fields.DateTime(format = 'iso')), **kwargs)

def query(endpoint: Url) -> JSONDict:
    """Queries an endpoint, returning a JSON dict."""
    headers = {'User-Agent' : USER_AGENT}
    uri = API_URL + endpoint
    response = requests.get(uri, headers = headers)
    response.raise_for_status()
    return response.json()


##############
# DATA MODEL #
##############

class SplitsIOData(DataClassJsonMixin):
    @classmethod
    def collection(cls) -> str:
        """Name of the API collection."""
        raise NotImplementedError
    @abstractproperty
    def canonical_id(self) -> str:
        """Canonical ID string with which to query an endpoint."""
    @classmethod
    def from_id(cls: Type[T], id_: str, **params: Any) -> T:
        """Constructs a data object from an ID string and any additional parameters."""
        endpoint = cls.collection() + '/' + str(id_)
        if params:
            endpoint += '?' + '&'.join(f'{key}={val}' for (key, val) in params.items())
        key = cls.__name__.lower()
        d = query(endpoint)[key]
        return cls.from_dict(d)
    def endpoint_prefix(self) -> str:
        """Endpoint prefix for an object with a particular ID."""
        return self.collection() + '/' + self.canonical_id + '/'
    def get_associated(self, cls: Type[T], name: str) -> List[T]:
        """Gets all associated objects of a certain type related to this one."""
        endpoint = self.endpoint_prefix() + name
        d = query(endpoint)
        return [cls.from_dict(item) for item in d[name]]

@dataclass
class Category(SplitsIOData):
    """A Category is a ruleset for a Game (Any%, 100%, MST, etc.) and an optional container for Runs. Its canonical ID string is a base 10 number, e.g. "312", "1456", "11"."""
    id: str
    name: str
    created_at: datetime = isodatetime(repr = False)
    updated_at: datetime = isodatetime(repr = False)
    @classmethod
    def collection(cls) -> str:
        return "categories"
    @property
    def canonical_id(self) -> str:
        return self.id
    def runs(self) -> List['Run']:
        """Runs for the category."""
        return self.get_associated(Run, 'runs')
    def runners(self) -> List['Runner']:
        """Runners for the category."""
        return self.get_associated(Runner, 'runners')

@dataclass
class Game(SplitsIOData):
    """A Game is a collection of information about a game, and a container for Categories. Its canonical ID string is its Speedrun.com shortname, e.g. "sms", "sm64", "portal"."""
    id: str
    name: str
    shortname: Optional[str]
    created_at: datetime = isodatetime(repr = False)
    updated_at: datetime = isodatetime(repr = False)
    categories: Optional[List[Category]] = field(default = None, repr = False)
    @classmethod
    def collection(cls) -> str:
        return "games"
    @property
    def canonical_id(self) -> str:
        return self.name if (self.shortname is None) else self.shortname
    @classmethod
    def all(cls) -> List['Game']:
        """Obtains the list of all games."""
        d = query('games')
        return [Game.from_dict(item) for item in d['games']]
    def runs(self) -> List['Run']:
        """Runs for the game."""
        return self.get_associated(Run, 'runs')
    def runners(self) -> List['Runner']:
        """Runners for the game."""
        return self.get_associated(Runner, 'runners')
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
    avatar: str = field(repr = False)
    created_at: datetime = isodatetime(repr = False)
    updated_at: datetime = isodatetime(repr = False)
    @classmethod
    def collection(cls) -> str:
        return "runners"
    @property
    def canonical_id(self) -> str:
        return self.name.lower()
    def runs(self) -> List['Run']:
        """The runner's runs."""
        return self.get_associated(Run, 'runs')
    def pbs(self) -> List['Run']:
        """The runner's personal best runs."""
        return self.get_associated(Run, 'pbs')
    def games(self) -> List[Game]:
        """Games for which the runner has at least one speedrun."""
        return self.get_associated(Game, 'games')
    def categories(self) -> List[Category]:
        """Categories the runner has participated in."""
        return self.get_associated(Category, 'categories')

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
    video_url: Optional[str]
    game: Optional[Game]
    category: Optional[Category]
    runners: List[Runner]
    segments: List[Segment] = field(repr = False)
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
        return super(Run, cls).from_id(id_, **params)