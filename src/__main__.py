import datetime
import json
import time

from . import db
from .airport import get_airport_by_icao
from .notify import notify

SLEEP_INTERVAL_SECONDS = 5 * 60

# Load startup IDs to allow tweeting missed flights on restart.
try:
    with open("start_at_ids.json") as file:
        latest_flights = json.load(file)
except (json.JSONDecodeError, FileNotFoundError):
    latest_flights = {}

# Clear startup IDs so they are not reused in case of crash or restart.
with open("start_at_ids.json", "w") as file:
    modified_start_up_ids = {key: None for key in latest_flights}
    json.dump(modified_start_up_ids, file)

check_count = 0
while True:
    with db.cursor() as cur:
        # Re-fetch watched aircraft every loop in case accounts are added/removed.
        cur.execute("""
            SELECT a.reg, COALESCE(f_max.id, -1) AS latest_flight_id
            FROM "plane-notify".aircraft a
            JOIN "plane-notify".twitter_accounts ta ON a.twitter_acc_id = ta.id
            JOIN (
                SELECT reg, MAX(id) AS id
                FROM "plane-notify".flights
                GROUP BY reg
            ) f_max ON a.reg = f_max.reg
            WHERE ta.delay IS TRUE;
        """)
        results = cur.fetchall()
        current_regs = []
        for result in results:
            if result["reg"] not in latest_flights or not latest_flights[result["reg"]]:
                latest_flights[result["reg"]] = result["latest_flight_id"]
            current_regs.append(result["reg"])

        # Remove registrations that are no longer being watched.
        for reg in list(latest_flights):
            if reg not in current_regs:
                latest_flights.pop(reg)

        print(f"Latest Flights: {latest_flights}")

        for reg, latest_id in list(latest_flights.items()):
            print(f"Checking {reg} for flights to post > {latest_id}:", end=" ")
            sql = """
                SELECT
                    f.id, f.callsign, f.origin, f.takeoff_confirmed,
                    f.destination, f.landing_confirmed, f.takeoff_time, f.landing_time
                FROM "plane-notify".flights f
                WHERE f.id > %(latest_id)s
                AND f.landing_time <= (timezone('utc', now()) - INTERVAL '24 HOURS')
                AND f.landing_time >= (timezone('utc', now()) - INTERVAL '72 HOURS')
                AND f.reg = %(reg)s
                ORDER BY f.takeoff_time ASC
            """
            cur.execute(sql, {"reg": reg, "latest_id": latest_id})
            if cur.rowcount == 0:
                print("None new")
                continue

            results = cur.fetchall()
            print(f"{len(results)} new flights")

            sql = """
                SELECT ta."@", tck."key", tck.secret, ta.access_token, ta.access_token_secret
                FROM "plane-notify".twitter_accounts ta,
                     "plane-notify".twitter_consumer_keys tck,
                     "plane-notify".aircraft a
                WHERE ta.id = a.twitter_acc_id
                AND a.reg = %(reg)s
                AND ta.api_id = tck.id
            """
            cur.execute(sql, {"reg": reg})
            twitter_details = cur.fetchone()

            for new_flight in results:
                new_flight = dict(new_flight)
                new_flight["reg"] = reg
                since_landing = (
                    datetime.datetime.now(datetime.timezone.utc) - new_flight["landing_time"]
                )
                hours, remainder = divmod(int(since_landing.total_seconds()), 3600)
                minutes = remainder // 60
                print(
                    f"\t New {new_flight['id']}, {new_flight['origin']} -> {new_flight['destination']},"
                    f" landed {hours} hours : {minutes} mins ago"
                )
                origin_airport = get_airport_by_icao(new_flight["origin"])
                destination_airport = get_airport_by_icao(new_flight["destination"])
                notify(new_flight, origin_airport, destination_airport, twitter_details, hours)
                latest_flights[reg] = new_flight["id"]

    check_count += 1
    # Rollback to keep the connection clean for the next iteration.
    db.conn.rollback()
    print(f"Sleeping.... checks: {check_count}")
    time.sleep(SLEEP_INTERVAL_SECONDS)
