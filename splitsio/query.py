from abc import abstractmethod, abstractproperty
from math import ceil
import requests
from typing import Any, Dict, overload, List, Mapping, Optional, Sequence, Tuple, Type, TypeVar, Union

from dataclasses_json import DataClassJsonMixin

D = TypeVar('D')
T = TypeVar('T', bound = 'SplitsIOData')
Header = Mapping[str, str]
JSONDict = Dict[str, Any]

API_URL = 'https://splits.io/api/v4/'
USER_AGENT = 'splitsio_api'


def query(endpoint: str) -> Tuple[Header, JSONDict]:
    """Queries an endpoint, returning two JSON dicts (response headers and content)."""
    headers = {'User-Agent' : USER_AGENT}
    uri = API_URL + endpoint
    response = requests.get(uri, headers = headers)
    response.raise_for_status()
    return (response.headers, response.json())

class Paginator(Sequence[D]):
    """A paginated sequence of items, obtaining each page only when needed."""
    def __init__(self, items_per_page: int, total_items: int) -> None:
        self.items_per_page = items_per_page
        self.total_items = total_items
        num_pages = ceil(total_items / items_per_page)
        self.pages: List[Optional[List[D]]] = [None] * num_pages
    @abstractmethod
    def load_page(self, pagenum: int) -> None:
        """Given a (0-up) page index, loads the corresponding page."""
    def _getitem(self, i: int) -> D:
        pagenum = i // self.items_per_page
        if (self.pages[pagenum] is None):
            self.load_page(pagenum)
        return self.pages[pagenum][i % self.items_per_page]  # type: ignore
    @overload
    def __getitem__(self, i: int) -> D:
        pass
    @overload
    def __getitem__(self, slc: slice) -> List[D]:
        pass
    def __getitem__(self, index: Union[int, slice]) -> Union[D, List[D]]:
        if isinstance(index, slice):
            return [self[i] for i in range(len(self))[index]]
        else:
            return self._getitem(index)
    def __len__(self) -> int:
        return self.total_items

class SplitsIOPaginator(Paginator[T]):
    """Paginator for SplitsIOData that assumes each page is accessible by affixing the page number to a base URI."""
    def __init__(self, cls: Type[T], endpoint: str, header: Header) -> None:
        self.cls = cls
        self.endpoint = endpoint
        items_per_page = int(header['Per-Page'])
        total_items = int(header['Total'])
        super().__init__(items_per_page, total_items)
    def load_page(self, pagenum: int) -> None:
        (_, d) = query(self.endpoint + '?page=' + str(pagenum + 1))
        self.pages[pagenum] = [self.cls.from_dict(item) for item in d[self.cls.collection()]]

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
        (_, d) = query(endpoint)
        return cls.from_dict(d[key])
    def endpoint_prefix(self) -> str:
        """Endpoint prefix for an object with a particular ID."""
        return self.collection() + '/' + self.canonical_id + '/'
    @classmethod
    def query(cls: Type[T], endpoint: str, key: Optional[str] = None) -> Sequence[T]:
        """Queries an endpoint and converts results (possibly paginated) to this type."""
        key = cls.collection() if (key is None) else key
        (header, d) = query(endpoint)
        if ('Per-Page' in header):
            # only have the first page, so return a paginator
            paginator = SplitsIOPaginator(cls, endpoint, header)
            # already have the first page, so store it
            paginator.pages[0] = [cls.from_dict(item) for item in d[key]]
            return paginator
        # otherwise, all the results have been obtained
        return [cls.from_dict(item) for item in d[key]]
    def get_associated(self, cls: Type[T], key: Optional[str] = None) -> Sequence[T]:
        """Gets all associated objects of a certain type related to this one."""
        key = cls.collection() if (key is None) else key
        endpoint = self.endpoint_prefix() + key
        return cls.query(endpoint, key = key)
