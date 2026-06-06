# plane-notify-delayed

An extension to [plane-notify](https://github.com/Jxck-S/plane-notify) that posts flights on a delay to comply with Twitter/X location policies. See [HISTORY.md](HISTORY.md) for background.

## How it works

Connects to the PostgreSQL database used by plane-notify, watches for aircraft that have Twitter accounts with delay mode enabled, and posts flights once they are at least 24 hours old (up to 72 hours) as of landing.

## Requirements

- Python 3.13+
- PostgreSQL database populated by [plane-notify](https://github.com/Jxck-S/plane-notify)
- `flight_static_maps` (private local dependency — must be present at project root)
- Dependencies via Pipfile: `pipenv install`

## Configuration

Copy `conf.ini.example` to `conf.ini` and fill in your database credentials:

```ini
[DB]
DB= tracking
USER= your_db_user
PW= your_db_password
PORT= 5432
HOST= your_db_host

[OPTIONS]
FUEL_CO2 = True
```

## Running

```bash
python -m src
```

Run from the project root so `conf.ini` and `start_at_ids.json` are resolved correctly.

## start_at_ids.json

On startup the app loads this file to know the last posted flight ID per aircraft, then clears it so stale IDs aren't reused after a crash or restart. It is gitignored — it will be created automatically on first run.

## Easter eggs

- Alt text :)
