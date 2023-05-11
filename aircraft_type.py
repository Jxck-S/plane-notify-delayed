def get_ac_type(cursor, reg):
	sql = """select icaotype  from deps.adsbx_ac aa where reg = %s"""
	cursor.execute(sql, (reg,))
	if cursor.rowcount > 0:
		icao_type = cursor.fetchone()['icaotype']
		return icao_type
	else:
		return None
