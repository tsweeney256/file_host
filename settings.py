# Example settings
#
# Please make your own settings file and map the environment variable
# FILE_HOST_SETTINGS to it

# Required settings
SERVER_NAME = 'localhost:5000'
SECRET_KEY = 'secret'
PASS_RESET_EXPR = '1 day'  # Time until the password reset request expires

# Optional settings
DEBUG = True  # Defaults to False

# PostgreSQL connection settings
# Refer to PostgreSQL's documentation for connection defaults
DBNAME = 'file_host'
DBUSER = 'file_host_user'
# DBPASS = 'password'
# DBPORT = 1234
# DBHOST = 'host'
