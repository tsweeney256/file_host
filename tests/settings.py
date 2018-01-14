import os

TESTING = True
SECRET_KEY = 'unittest'
SERVER_NAME = 'file_host'
DBNAME = 'file_host_unit_test'
DBUSER = 'file_host_unit_test'
DBPASS = 'file_host_unit_test'
DBPORT = '5001'
DBHOST = os.path.dirname(os.path.realpath(__file__)) + '/data'
PASS_RESET_EXPR = '1 day'
