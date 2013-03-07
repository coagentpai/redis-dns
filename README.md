redis-dns
=========

A gevent redis based DNS server with dyndns like API

Prerequisites:
--------------

- [gevent](http://www.gevent.org/)
- [redis-server](http://www.redis.io/)
- [dnspython](http://www.dnspython.org/)

Setup
--------------

To set the zone to serve call the zone subcommand (the zone will be stored in redis)
For example if your domain was example.com:
```redis-dns zone example.com ns1.example.com ns2.example.com``` 

Then add some users:
```redis-dns users -a <username> <password> <subdomain>```

To start invoke:
```redis-dns run```

For an example systemd service file see redis-dns.service.
