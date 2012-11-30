import redis
from gevent import socket

class Connection(redis.connection.Connection):
    def _connect(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.socket_timeout)
        sock.connect((self.host, self.port))
        return sock
    pass # END Class Connection

