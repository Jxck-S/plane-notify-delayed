import logging
import os
from typing import Optional

from geopy.distance import geodesic

from . import config, x_client
from .aircraft_type import get_ac_type
from .airport import airport_code
from .flight_map import create_flight_map
from .fuel_calc import fuel_calculation, fuel_message

logger = logging.getLogger(__name__)

MI_TO_NM = 1.150779448


def notify(
    flight: dict,
    origin_airport: dict,
    destination_airport: dict,
    x_details: Optional[dict] = None,
    hours_since: Optional[int] = None,
) -> None:
    """Post flight details to X and print a notification summary.

    Args:
        flight: Flight data dictionary.
        origin_airport: Origin airport details from get_airport_by_code().
        destination_airport: Destination airport details from get_airport_by_code().
        x_details: X API credentials dict, also carrying the aircraft title and the
            account's fleet_size, or None to skip posting.
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
        # Airports with no published code fall back to their municipality: the
        # OurAirports ident is a generated placeholder ("US-1234") for those.
        origin_code = airport_code(origin_airport) or origin_airport["municipality"]
        dest_code = airport_code(destination_airport) or destination_airport["municipality"]
        second_message = (
            f"{'{:,}'.format(round(distance_mi))} mile"
            f" ({'{:,}'.format(round(distance_nm))} NM)"
            f" flight from {origin_code} to {dest_code}"
        )

    if config.FUEL_CO2:
        ac_type = get_ac_type(flight["reg"])
        if ac_type is not None:
            logger.info("Running fuel info calc")
            flight_time_min = flight_time.total_seconds() / 60
            fuel_info = fuel_calculation(ac_type, flight_time_min)
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
    # Accounts tracking a single aircraft don't need the title for disambiguation.
    title = x_details.get("title") if x_details else None
    if title and x_details.get("fleet_size", 0) > 1:
        flew_clause = f"{title} flew from"
    else:
        flew_clause = "Flew from"

    message = (
        f"{flew_clause} {origin_location} to {destination_location} {time_ago_wording}."
        f"\n{landed_time_msg}"
    )

    logger.info(message)

    try:
        if x_details and x_details.get("account_disabled"):
            logger.warning("Skipping post to @%s: account is disabled", x_details["@"])
        elif x_details and x_details.get("app_disabled"):
            logger.warning("Skipping post to @%s: app is disabled", x_details["@"])
        elif x_details and not (x_details["access_token"] and x_details["access_token_secret"]):
            logger.warning(
                "Skipping post to @%s: access_token/access_token_secret missing", x_details["@"]
            )
        elif x_details:
            logger.info("Posting flight to @%s", x_details["@"])
            # Identifiers go last so screen readers lead with the picture, not metadata.
            identifiers = [f"Reg: {flight['reg']}"]
            if flight["icao"]:
                identifiers.append(f"ICAO: {flight['icao']}")
            if flight["callsign"]:
                identifiers.append(f"Callsign: {flight['callsign']}")
            identifiers.append(f"Origin: {flight['origin']}")
            identifiers.append(f"Destination: {flight['destination']}")
            alt_text = (
                f"Map showing a blue line from {origin_location} to"
                f" {destination_location}, with an aircraft icon at the destination.\n"
                "Aircraft and flight info:\n"
                + " ".join(identifiers)
            )
            media_id = x_client.upload_media(x_details, flight_map_image_name, alt_text)
            post_id = x_client.create_post(x_details, message, media_ids=[media_id])
            if second_message:
                x_client.create_post(x_details, second_message, in_reply_to_post_id=post_id)
    finally:
        os.remove(flight_map_image_name)
