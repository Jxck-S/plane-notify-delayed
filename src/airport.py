from typing import Optional

from . import db


def get_airport_by_code(code: str) -> Optional[dict]:
    """Fetch airport details by OurAirports ident, falling back to GPS code.

    'ident' is the OurAirports primary key: always populated, unique, and equal
    to the ICAO code when the airport has one. It is what plane-notify stores
    for new flights. Historical rows instead hold 'icao_code' (blank for most
    small airports), which is a subset of 'gps_code', so a miss on ident is
    retried against gps_code to keep those flights resolvable.

    Args:
        code: OurAirports ident, or a legacy ICAO/GPS code.

    Returns:
        Dict with airport data (with 'icao' key instead of 'gps_code'),
        or None if not found or the code is blank.
    """
    # OurAirports stores an empty string, not NULL, for airports with no GPS
    # code (~41k rows), so a blank lookup would otherwise match an arbitrary
    # one of them rather than returning nothing.
    if not code:
        return None

    sql = """
        SELECT
            oaa.ident, oaa.type, oaa.name, oaa.lat, oaa.lon, oaa.elev,
            oaa.continent, oaa.iso_country, oaa.iso_region, oaa.municipality,
            oaa.gps_code, oaa.icao_code, oaa.iata_code, oaa.local_code,
            oar.name AS region
        FROM deps.our_airports_airports oaa, deps.our_airports_regions oar
        WHERE oaa.{column} = %s AND oaa.{column} <> '' AND oaa.iso_region = oar.code
        LIMIT 1;
    """
    with db.cursor() as cur:
        for column in ("ident", "gps_code"):
            cur.execute(sql.format(column=column), (code,))
            if cur.rowcount > 0:
                airport = dict(cur.fetchone())
                break
        else:
            return None
    airport["icao"] = airport.pop("gps_code")
    return airport


def airport_code(airport: dict) -> Optional[str]:
    """Return the code to show for an airport, or None if it has no real one.

    Deliberately excludes 'ident': for the ~45k airports with no published
    code, OurAirports generates a placeholder ident such as 'US-1234', which is
    meaningless in a post.
    """
    return airport["iata_code"] or airport["icao_code"] or airport["local_code"] or None
