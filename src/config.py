import configparser

_conf = configparser.ConfigParser()
_conf.read("conf.ini")

# Database
DB_NAME = _conf.get("DB", "DB")
DB_USER = _conf.get("DB", "USER")
DB_PASSWORD = _conf.get("DB", "PW")
DB_HOST = _conf.get("DB", "HOST")
DB_PORT = _conf.get("DB", "PORT")

# Options
FUEL_CO2 = _conf.getboolean("OPTIONS", "FUEL_CO2")
