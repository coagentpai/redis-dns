import redis
from gevent import socket

class Connection(redis.connection.Connection):
    """An event loop friendly redis connection"""
    def _connect(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.socket_timeout)
        sock.connect((self.host, self.port))
        return sock
    pass # END Class Connection

def get_redis():
    return __connection

def connect_redis(host='localhost', port=6379):
    pool = redis.ConnectionPool(connection_class=Connection)
    conn = redis.Redis(host=host, port=port, connection_pool=pool)
    return conn

def setup_connection(host, port):
    __connection = connect_redis()
    return __connection
    pass

__connection = connect_redis()
__all__ = [ 'get_redis' ]

