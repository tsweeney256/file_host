import os

TESTING = True
SECRET_KEY = 'unittest'
SERVER_NAME = 'file_host'
DBUSER = os.environ['USER']
DBNAME = 'file_host_unit_test'
DBPORT = '5001'
DBHOST = os.path.dirname(os.path.realpath(__file__)) + '/data'
