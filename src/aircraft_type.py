from typing import Optional

from . import db


def get_ac_type(reg: str) -> Optional[str]:
    """Fetch aircraft ICAO type from the database by registration number.

    Args:
        reg: Aircraft registration (tail number).

    Returns:
        ICAO aircraft type code, or None if not found.
    """
    sql = """SELECT icaotype FROM deps.adsbx_ac aa WHERE reg = %s"""
    with db.cursor() as cur:
        cur.execute(sql, (reg,))
        if cur.rowcount > 0:
            return cur.fetchone()["icaotype"]
    return None
