import logging
from typing import Optional

from . import db

logger = logging.getLogger(__name__)

GALLONS_TO_KG = 3.04
GALLONS_TO_LITERS = 3.78541
KG_TO_LBS = 2.20462
KG_TO_CO2_TONS_FACTOR = 3.15
KG_TO_TONS = 907.185
MINUTES_PER_HOUR = 60


def get_avg_fuel_price() -> Optional[float]:
    """Fetch average fuel price per gallon from the database.

    Returns:
        Average fuel price as float, or None if unavailable.
    """
    sql = """SELECT cost::numeric::float FROM "plane-notify".fuel"""
    with db.cursor() as cur:
        cur.execute(sql)
        if cur.rowcount > 0:
            cost = cur.fetchone()["cost"]
            logger.info("AVG fuel cost per gallon is $%s", cost)
            return cost
    return None


def fuel_calculation(aircraft_icao_type: str, minutes: float) -> Optional[dict]:
    """Calculate fuel usage, price, and CO2 output for a flight.

    Args:
        aircraft_icao_type: ICAO aircraft type code.
        minutes: Flight duration in minutes.

    Returns:
        Dict with fuel stats, or None if aircraft type is unknown.
    """
    sql = """SELECT galph FROM "plane-notify".icao_type_info WHERE icao_code = %s"""
    with db.cursor() as cur:
        cur.execute(sql, (aircraft_icao_type,))
        if cur.rowcount == 0:
            logger.warning("Can't calculate fuel info: unknown aircraft ICAO type %s", aircraft_icao_type)
            return None
        galph = cur.fetchone()["galph"]
    avg_fuel_price_per_gallon = get_avg_fuel_price()
    fuel_used_gal = galph * (minutes / MINUTES_PER_HOUR)
    fuel_used_kg = fuel_used_gal * GALLONS_TO_KG
    co2_tons = (fuel_used_kg * KG_TO_CO2_TONS_FACTOR) / KG_TO_TONS

    fuel_flight_info = {
        "fuel_used_gal": round(fuel_used_gal),
        "fuel_used_kg": round(fuel_used_kg),
        "fuel_used_liters": round(fuel_used_gal * GALLONS_TO_LITERS),
        "fuel_used_lbs": round(fuel_used_kg * KG_TO_LBS),
        "co2_tons": round(co2_tons) if co2_tons > 1 else round(co2_tons, 4),
    }
    if avg_fuel_price_per_gallon:
        fuel_flight_info["fuel_price"] = round(fuel_used_gal * avg_fuel_price_per_gallon)

    return fuel_flight_info


def fuel_message(fuel_info: dict) -> str:
    """Format fuel calculation results into a readable string.

    Args:
        fuel_info: Dictionary from fuel_calculation().

    Returns:
        Formatted multi-line string with fuel and emissions details.
    """
    gallons = "{:,}".format(fuel_info["fuel_used_gal"])
    liters = "{:,}".format(fuel_info["fuel_used_liters"])
    lbs = "{:,}".format(fuel_info["fuel_used_lbs"])
    kgs = "{:,}".format(fuel_info["fuel_used_kg"])

    if "fuel_price" in fuel_info:
        cost_line = f"~ ${'{:,}'.format(fuel_info['fuel_price'])} cost of fuel."
    else:
        cost_line = "Cost of fuel unavailable"

    return (
        f"\n~ {gallons} gallons ({liters} liters)."
        f"\n~ {lbs} lbs ({kgs} kg) of jet fuel used."
        f"\n{cost_line}"
        f"\n~ {fuel_info['co2_tons']} tons of CO2 emissions."
    )
