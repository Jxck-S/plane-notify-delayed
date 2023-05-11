def get_airport_by_icao(cursor, icao):
    sql = """SELECT oaa.ident, oaa.type, oaa.name, oaa.lat, oaa.lon, oaa.elev, oaa.continent, oaa.iso_country, oaa.iso_region, oaa.municipality, oaa.gps_code, oaa.iata_code, oaa.local_code,
	oar.name as region
	FROM deps.our_airports_airports oaa, deps.our_airports_regions oar
	WHERE oaa.gps_code = %s AND oaa.iso_region = oar.code
	LIMIT 1;
	"""
    cursor.execute(sql, [icao])
    if cursor.rowcount > 0:
        airport_dict = dict(cursor.fetchone())
        airport_dict['icao'] = airport_dict.pop('gps_code')
    else:
        airport_dict = None
    return airport_dict