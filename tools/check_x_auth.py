"""Read-only credential check for every x_accounts row.

Calls GET /2/users/me for each account (no posting, no media, minimal
rate-limit cost) and reports whether its stored access_token/access_token_secret
are currently valid against its assigned app.

Usage:
    pipenv run python tools/check_x_auth.py
"""

import os
import sys

import psycopg2
import psycopg2.extras
import requests
from requests_oauthlib import OAuth1

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import config

USERS_ME_URL = "https://api.x.com/2/users/me"
REQUEST_TIMEOUT = 15


def main() -> None:
    conn = psycopg2.connect(
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        host=config.DB_HOST,
        port=config.DB_PORT,
        application_name="check-x-auth",
    )
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(
        """
        SELECT xa.id, xa."@", xa.api_id, xa.disabled, xck."key", xck.secret,
               xa.access_token, xa.access_token_secret
        FROM "plane-notify".x_accounts xa
        JOIN "plane-notify".x_consumer_keys xck ON xa.api_id = xck.id
        ORDER BY xa.id
        """
    )
    rows = cur.fetchall()
    conn.close()

    for row in rows:
        if row["disabled"]:
            print(f"[SKIPPED] id={row['id']} @{row['@']} (api_id={row['api_id']}): disabled")
            continue

        if not (row["access_token"] and row["access_token_secret"]):
            print(
                f"[FAIL] id={row['id']} @{row['@']} (api_id={row['api_id']}): "
                "access_token/access_token_secret missing but account is not disabled"
            )
            continue

        auth = OAuth1(
            row["key"],
            client_secret=row["secret"],
            resource_owner_key=row["access_token"],
            resource_owner_secret=row["access_token_secret"],
        )
        resp = requests.get(USERS_ME_URL, auth=auth, timeout=REQUEST_TIMEOUT)
        status = "OK" if resp.status_code == 200 else "FAIL"
        print(f"[{status}] id={row['id']} @{row['@']} (api_id={row['api_id']}): {resp.status_code} {resp.text[:150]}")


if __name__ == "__main__":
    main()
