from typing import Optional

from . import db


def get_airport_by_icao(icao: str) -> Optional[dict]:
    """Fetch airport details by ICAO/GPS code.

    Args:
        icao: ICAO/GPS code of the airport.

    Returns:
        Dict with airport data (with 'icao' key instead of 'gps_code'),
        or None if not found.
    """
    sql = """
        SELECT
            oaa.ident, oaa.type, oaa.name, oaa.lat, oaa.lon, oaa.elev,
            oaa.continent, oaa.iso_country, oaa.iso_region, oaa.municipality,
            oaa.gps_code, oaa.iata_code, oaa.local_code,
            oar.name AS region
        FROM deps.our_airports_airports oaa, deps.our_airports_regions oar
        WHERE oaa.gps_code = %s AND oaa.iso_region = oar.code
        LIMIT 1;
    """
    with db.cursor() as cur:
        cur.execute(sql, (icao,))
        if cur.rowcount == 0:
            return None
        airport = dict(cur.fetchone())
    airport["icao"] = airport.pop("gps_code")
    return airport
