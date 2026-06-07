from typing import Optional


def get_ac_type(cursor, reg: str) -> Optional[str]:
    """Fetch aircraft ICAO type from the database by registration number.

    Args:
        cursor: Database cursor.
        reg: Aircraft registration (tail number).

    Returns:
        ICAO aircraft type code, or None if not found.
    """
    sql = """SELECT icaotype FROM deps.adsbx_ac aa WHERE reg = %s"""
    cursor.execute(sql, (reg,))
    if cursor.rowcount > 0:
        return cursor.fetchone()["icaotype"]
    return None
