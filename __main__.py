import psycopg2
import psycopg2.extras
import time
import datetime
import configparser
from airport import get_airport_by_icao
from notify import notify
conf = configparser.ConfigParser()
conf.read('conf.ini')
conn = psycopg2.connect(
    dbname=conf.get("DB", "DB"),
    user=conf.get("DB", "USER"),
    password=conf.get("DB", "PW"),
    host=conf.get("DB", "HOST"),
    port=conf.get("DB", "PORT")
)

import json
#Load up IDs if you need to Tweet missed flights or similar. 
with open('start_at_ids.json') as file:
    latest_flights = json.load(file)


# Clear startup IDs, so it doesn't reuse same id's incase of crash or restart
with open('start_at_ids.json', 'w') as file:
    modified_start_up_ids = {key: None for key in latest_flights}
    json.dump(modified_start_up_ids, file)
count = 0
while True:
    # Create a cursor with a dictionary cursor
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # Get Aircrafts to watch for and current latest flight for each aircraft, this is run every check incase new aircraft/twitter accounts are added
    cur.execute(f"""SELECT a.reg, COALESCE(f_max.id, -1) as latest_flight_id
        FROM "plane-notify".aircraft a
        JOIN "plane-notify".twitter_accounts ta ON a.twitter_acc_id = ta.id
        JOIN (
        SELECT reg, MAX(id) AS id
        FROM "plane-notify".flights
        GROUP BY reg
        ) f_max ON a.reg = f_max.reg
        WHERE ta.delay IS TRUE; """)
    results = cur.fetchall()
    current_regs = []
    for result in results:
        #Adding new tail to check for flights
        if result['reg'] not in latest_flights.keys():
            latest_flights[result['reg']] = result['latest_flight_id']
        #Use for next loop
        current_regs.append(result['reg'])
    #Remove ones that should no longer be checked
    for reg in latest_flights.copy().keys():
        if reg not in current_regs:
            latest_flights.pop(reg)
    print(f"Latest Flights: {latest_flights}")


    # Execute the query for each aircraft in the dictionary
    for reg, latest_id in latest_flights.copy().items():
        print(f"Checking {reg} for flights to post > {latest_id}:", end=" ")
        # Define the SQL query to retrieve new flight records for each aircraft
        sql = """
        SELECT f.id, f.callsign, f.origin, f.takeoff_confirmed, f.destination, f.landing_confirmed, f.takeoff_time, f.landing_time
        FROM "plane-notify".flights f
        where  f.id > %(latest_id)s
        AND f.landing_time < (timezone('utc', now()) - INTERVAL '24 HOURS')
        and f.reg = %(reg)s
        ORDER BY f.takeoff_time ASC
        """
        # Execute the query and fetch the results
        cur.execute(sql, {'reg': reg, 'latest_id': latest_id})
        if cur.rowcount == 0:
            print("None new")
        else:
            results = cur.fetchall()
            print(f"{len(results)} new flights")
            #Retrive Twitter Details
            sql = """
                SELECT ta."@", tck."key", tck.secret ,ta.access_token, ta.access_token_secret
                FROM "plane-notify".twitter_accounts ta, "plane-notify".twitter_consumer_keys tck, "plane-notify".aircraft a
                WHERE ta.id = a.twitter_acc_id
                AND a.reg = %(reg)s
                AND ta.api_id = tck.id"""
            cur.execute(sql, {"reg": reg})
            twitter_details = cur.fetchone()

            # Process the flight results
            for new_flight in results:
                new_flight = dict(new_flight)
                new_flight['reg'] = reg
                since_landing = datetime.datetime.utcnow() - new_flight['landing_time']
                hours, remainder = divmod(int(since_landing.total_seconds()), 3600)
                minutes = int(remainder / 60)
                print(f"\t New {new_flight['id']}, {new_flight['origin']} -> {new_flight['destination']}, landed {hours} hours : {minutes} mins ago")
                origin_airport = get_airport_by_icao(cur, new_flight['origin'])
                destination_airport = get_airport_by_icao(cur,new_flight['destination'])
                notify(cur, new_flight, origin_airport, destination_airport, twitter_details, hours)
                latest_flights[reg] = new_flight['id']
    cur.close()
    count += 1
    conn.rollback()
    print(f"sleeping.... checks: {count}")
    time.sleep(5*60)