SQLALCHEMY_DATABASE_URI = "sqlite:////tmp/corvus-web.db"
SQLALCHEMY_TRACK_MODIFICATIONS = True
SQLALCHEMY_POOL_RECYCLE = 1500

REDIS_CONFIG_CMD = 'ele-super-config'
VENV = '/srv/virtualenvs/corvus-web'
INDEX_URL = 'http://pypi.python.org/simple'

RSYSLOG_PATH = '/etc/rsyslog.d/30-corvus.conf'
LOGROTATE_PATH = '/etc/logrotate.d/corvus'

HUSKAR_API_HOST = 'localhost'
HUSKAR_API_PORT = 8020
HUSKAR_TEAM = 'arch'
HUSKAR_TOKEN = 'test_token'

# cache
CACHE_REDIS_DSN = 'redis://localhost:6379'
CACHE_UPDATE_INTERVAL = 10

ARCHIVE_DIRECTORY = '/srv/corvus-web/archives'
ARCHIVE_ADDRESS = 'http://localhost/api/archive'

SASH_HOST = "localhost"
SASH_PORT = 80
