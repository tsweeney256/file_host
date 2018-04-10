import getpass


# Example settings
#
# Please make your own settings file and map the environment variable
# FILE_HOST_SETTINGS to it

SERVER_NAME = 'localhost:5000'
SECRET_KEY = 'secret'
# Time for email confirmations to expire
CONFIRM_EXPR = '1 day'

# Optional settings
DEBUG = True  # Defaults to False
INDEX = 'index.index'  # Defaults to 'index.index'

# PostgreSQL connection settings
# Refer to PostgreSQL's documentation for connection defaults
DBNAME = 'file_host'
DBUSER = 'file_host_user'
# DBPASS = 'password'
# DBPORT = 1234
# DBHOST = 'host'

# Flask-Mail settings
# Refer to Flask-Mail's documentation
# MAIL_SERVER = 'localhost'
# MAIL_PORT = 25
# MAIL_USE_TKS = False
# MAIL_USE_SSL = False
# MAIL_DEBUG = DEBUG # Defaults to app.debug
# MAIL_USERNAE = None
# MAIL_PASSWORD = None
MAIL_DEFAULT_SENDER = getpass.getuser()
# MAIL_MAX_EMAILS = None
# MAIL_SUPPRESS_SEND = False # Defaults to app.testing
# MAIL_ASCII_ATTACHMENTS = False
