import os
from typing import Optional

import tweepy
from geopy.distance import geodesic

from . import config
from .aircraft_type import get_ac_type
from .flight_map import create_flight_map
from .fuel_calc import fuel_calculation, fuel_message

MI_TO_NM = 1.150779448


def notify(
    cur,
    flight: dict,
    origin_airport: dict,
    destination_airport: dict,
    twitter_details: Optional[dict] = None,
    hours_since: Optional[int] = None,
) -> None:
    """Post flight details to Twitter and print a notification summary.

    Args:
        cur: Database cursor.
        flight: Flight data dictionary.
        origin_airport: Origin airport details from get_airport_by_icao().
        destination_airport: Destination airport details from get_airport_by_icao().
        twitter_details: Twitter API credentials dict, or None to skip posting.
        hours_since: Hours since the flight landed, used for message wording.
    """
    origin_coords = (origin_airport["lat"], origin_airport["lon"])
    destination_coords = (destination_airport["lat"], destination_airport["lon"])
    flight_map_image_name = f"{flight['reg']}_{flight['id']}_flight_map.png"
    create_flight_map(origin_coords, destination_coords, flight_map_image_name)

    # Flight time
    flight_time = flight["landing_time"] - flight["takeoff_time"]
    hours, remainder = divmod(flight_time.total_seconds(), 3600)
    minutes, _ = divmod(remainder, 60)
    min_syntax = "Mins" if minutes > 1 else "Min"
    if hours > 0:
        hour_syntax = "Hours" if hours > 1 else "Hour"
        time_suffix = f" : {int(minutes)} {min_syntax}. " if minutes > 0 else ". "
        landed_time_msg = f"Apx. flt. time {int(hours)} {hour_syntax}{time_suffix}"
    else:
        landed_time_msg = f"Apx. flt. time {int(minutes)} {min_syntax}."

    second_message = None

    if flight["origin"] != flight["destination"]:
        distance_mi = float(geodesic(origin_coords, destination_coords).mi)
        distance_nm = distance_mi / MI_TO_NM
        origin_code = origin_airport["iata_code"] or origin_airport["ident"]
        dest_code = destination_airport["iata_code"] or destination_airport["ident"]
        second_message = (
            f"{'{:,}'.format(round(distance_mi))} mile"
            f" ({'{:,}'.format(round(distance_nm))} NM)"
            f" flight from {origin_code} to {dest_code}"
        )

    if config.FUEL_CO2:
        ac_type = get_ac_type(cur, flight["reg"])
        if ac_type is not None:
            print("Running fuel info calc")
            flight_time_min = flight_time.total_seconds() / 60
            fuel_info = fuel_calculation(cur, ac_type, flight_time_min)
            if fuel_info is not None:
                fuel_line = fuel_message(fuel_info)
                second_message = f"{second_message}\n{fuel_line}" if second_message else fuel_line

    origin_location = (
        f"{origin_airport['municipality']}, {origin_airport['region']}, {origin_airport['iso_country']}"
    )
    destination_location = (
        f"{destination_airport['municipality']}, {destination_airport['region']}, {destination_airport['iso_country']}"
    )

    time_ago_wording = (
        "24 hours ago" if hours_since is not None and hours_since <= 24
        else f"on {flight['landing_time'].strftime('%-m/%-d')}"
    )
    message = f"Flew from {origin_location} to {destination_location} {time_ago_wording}.\n{landed_time_msg}"

    print(message)

    if twitter_details:
        print(f"Posting flight to @{twitter_details['@']}")
        auth = tweepy.OAuthHandler(twitter_details["key"], twitter_details["secret"])
        auth.set_access_token(twitter_details["access_token"], twitter_details["access_token_secret"])
        v1_tweet_api = tweepy.API(auth, wait_on_rate_limit=True)
        twitter_media_map_obj = v1_tweet_api.media_upload(flight_map_image_name)
        alt_text = f"Reg: {flight['reg']} Flight Map"
        v1_tweet_api.create_media_metadata(
            media_id=twitter_media_map_obj.media_id,
            alt_text=alt_text,
        )
        v2_tweet_api = tweepy.Client(
            consumer_key=twitter_details["key"],
            consumer_secret=twitter_details["secret"],
            access_token=twitter_details["access_token"],
            access_token_secret=twitter_details["access_token_secret"],
        )
        try:
            tweet_rsp = v2_tweet_api.create_tweet(
                text=message, media_ids=[twitter_media_map_obj.media_id]
            )
            tweet_id = tweet_rsp.data["id"]
            if second_message:
                v2_tweet_api.create_tweet(text=second_message, in_reply_to_tweet_id=tweet_id)
        except tweepy.HTTPException as e:
            if e.response is not None and e.response.status_code == 429:
                print("x-rate-limit-reset:", e.response.headers.get("x-rate-limit-reset"))
            raise

    os.remove(flight_map_image_name)
