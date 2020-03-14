# `splitsio`

A Python implementation of the [`splits.io`](https://splits.io) [REST API](https://github.com/glacials/splits-io/blob/master/docs/api.md).

`splitsio` currently supports read-only access. To upload runs, use the REST API directly.

Requires Python 3.7 or greater.

To install: `pip3 install splitsio`

Then to access the main data types in Python:

`import splitsio`

## Resource Types

### Game

#### Get information about a game

```python
>>> sms = Game.from_id('sms')
>>> sms
Game(id='15', name='Super Mario Sunshine', shortname='sms')
>>> sms.created_at
'2014-04-18T06:28:59.764Z'
```

NOTE: for games, the identifier for querying is the `shortname` (here `'sms'`), *not* the numerical `id`.

#### Get all games in the database

```python
>>> games = Game.all()  # this can take a minute or so
>>> len(games)
17237
>>> games[0]
Game(id='2206', name='007: Agent Under Fire', shortname='auf')
```

### Category

#### Get the speedrun categories for a game

```python
>>> oot = Game.from_id('oot')
>>> oot.categories[0]
Category(id='86832', name='No ACE')
```

#### Get category from id

```python
>>> no_ace = Category.from_id('86832')
>>> no_ace
Category(id='86832', name='No ACE')
```

### Runner

#### Get runners for a game or category

```python
>>> oot_runners = Game.from_id('oot').runners()
>>> len(oot_runners)
238
>>> oot_runners[0]
Runner(id='35', twitch_id='31809791', twitch_name='cma2819', display_name='cma2819', name='cma2819')
>>> no_ace_runners = no_ace.runners()
>>> no_ace_runners[0]
Runner(id='32189', twitch_id='63370787', twitch_name='bigmikey_', display_name='bigmikey_', name='bigmikey_')
```

#### Get runner from id

```python
>>> bigmikey = Runner.from_id('bigmikey_')
>>> bigmikey
Runner(id='32189', twitch_id='63370787', twitch_name='bigmikey_', display_name='bigmikey_', name='bigmikey_')
```

NOTE: for runners, the identifier for querying is the `name` all lowercased (here `'bigmikey_'`), *not* the numerical `id`.

### Run

#### Get runs for a game, category, or runner

```python
>>> oot_runs = Game.from_id('oot').runs()
>>> run = oot_runs[0]
>>> run.realtime_duration_ms
1507300
>>> run.program
'livesplit'
>>> run.attempts
97
>>> len(Category.from_id('86832').runs())
11
>>> len(Runner.from_id('bigmikey_').runs())
2
```

#### Get attempt histories for a run and its segments

```python
>>> run = Game.from_id('oot').runs()[0]
>>> run = Run.from_id(run.id, historic = True)
>>> len(run.histories)
90
>>> run.histories[1]
History(attempt_number=89, realtime_duration_ms=1507300, gametime_duration_ms=None, started_at='2020-03-10T20:06:08.000Z', ended_at='2020-03-10T20:31:15.000Z')
>>> run.segments[0].name
'Sword Get'
>>> len(run.segments[0].histories)
67
>>> run.segments[0].histories[0]
History(attempt_number=2, realtime_duration_ms=271832, gametime_duration_ms=0, started_at=None, ended_at=None)
```
