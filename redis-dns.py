#!/usr/bin/env python
import gevent
import gevent.pywsgi
from gevent import socket
import gevent.dns

import dns.message
import dns.rdata
from functools import partial
import logging
import redis
import sys
import urlparse
import json
import datetime

import gredis
import records

def dns_handler(s, peer, data, r, zone):
    request = dns.message.from_wire(data)
    reply = dns.message.make_response(request)
    reply.flags |= dns.flags.AA
    reply.flags &= ~dns.flags.RA
    # We only answer the first question
    q = request.question[0]
    name = q.name
    rdtype = q.rdtype
    if name.is_subdomain(zone):
        IP = r.hget("NODE:%s" % name, 'A')
        TXT = r.hget("NODE:%s" % name, 'TXT')
        IPV6 = r.hget("NODE:%s" % name, 'AAAA')
        if not IP:
            reply.set_rcode(dns.rcode.NXDOMAIN)
            pass
        else:
            if rdtype == dns.rdatatype.A:
                reply.answer.append(dns.rrset.from_rdata(name, 1800, records.A(IP)))
                pass
            elif rdtype == dns.rdatatype.MX:
                reply.answer.append(dns.rrset.from_rdata(name, 1800, records.MX(10, name)))
                reply.additional.append(dns.rrset.from_rdata(name, 1800, records.A(IP)))
                if TXT is not None:
                    reply.additional.append(dns.rrset.from_rdata(name, 1800, records.TXT(TXT)))
                    pass
                pass
            else:
                if TXT is not None:
                    reply.additional.append(dns.rrset.from_rdata(name, 1800, records.TXT(TXT)))
                    pass
                pass
            pass
    else:
        reply.set_rcode(dns.rcode.REFUSED)
        pass
    s.sendto(reply.to_wire(), peer)


def dns_failure(s, peer, data, greenlet):
    logging.error(greenlet.exception)
    try:
        request = dns.message.from_text(data)
        reply = dns.message.make_response(request)
        respone.set_rcode(dns.rcode.SERVFAIL)
        s.sendto(reply.to_wire(), peer)
    except Exception as e:
        # Bad request? Should we reply? What would be the id?,
        pass

def valid_auth(username, password, domain=None, r=None):
    if not r.hget('USER:%s' % username, 'password') == password:
        return False
    if not r.sismember('DOMAIN:%s' % username, domain):
        return False
    return True

def add_user(username, password, domain, r=None):
    r.hset('USER:%s' % username, 'password', password)
    r.sadd('DOMAIN:%s' % username, domain)
    pass

def web_service_handler(env, start_response):
    r = web_service_handler.r
    def format_json(node):
        node_name = node.lstrip('NODE:')
        records = [{'type': key, 'value': value} for key, value in r.hgetall(node).items() if key != 'UPDATED']
        return (node_name, {'records': records, 'updated':  r.hget(node, 'UPDATED')})

    if env['PATH_INFO'] == '/info':
        records = r.keys('NODE:*') 
        start_response('200 OK', [('Content-Type', 'application/json'), ('Access-Control-Allow-Origin', '*')])
        records = dict(map(format_json, records))
        return [ json.dumps(records) ]
        pass

    if env['PATH_INFO'] == '/update':
        args = urlparse.parse_qs(env['QUERY_STRING'])
        try:
            # Basic <base64 encoded - username:password> 
            username, password = env['HTTP_AUTHORIZATION'].split()[1].decode('base64').split(':')
            hostname = dns.name.from_unicode(unicode(args['hostname'].pop()))
            if not valid_auth(username, password, hostname, r=web_service_handler.r):
                start_response('401 Not Authorized', [('Content-Type', 'text/plain')])
                return ['Not Authorized\n']
            ip = args['myip'].pop()
            r.hmset('NODE:%s' % hostname, {'A': ip, 'UPDATED': datetime.datetime.utcnow().isoformat() + 'Z'})
            pass
        except KeyError as e:
            start_response('400 Bad Request', [('Content-Type', 'text/plain')])
            return ['Bad Request\n']
            pass
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return ['\n']
    else:
        start_response('404 Not Found', [('Content-Type', 'text/plain')])
        return ['Not Found\n']


def web_service(zone, r):
    web_service_handler.r = r
    server = gevent.pywsgi.WSGIServer(('0.0.0.0', 8080), web_service_handler)
    server.start()
    pass

def connect_redis():
    pool = redis.ConnectionPool(connection_class=gredis.Connection)
    r = redis.Redis(connection_pool=pool)
    return r

def serve(zone):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('0.0.0.0', 53))
    r = connect_redis()
    web_service(zone, r)
    dns_zone = dns.name.from_unicode(unicode(zone))
    while True:
        data,peer = s.recvfrom(8192)
        dns_greenlet = gevent.spawn(dns_handler, s, peer, data, r, dns_zone) 
        dns_greenlet.link_exception(partial(dns_failure, s, peer, data))


if __name__ == '__main__':
    # Be a good Unix daemon
    import argparse
    import daemon
    parser = argparse.ArgumentParser(description='Greenlet dynamic DNS server')
    parser.add_argument('zone', metavar='ZONE', type=unicode, help='Zone to serve (e.g example.com)')
    parser.add_argument('-b', '--background', dest='background', action='store_true', help='Background the server')
    parser.add_argument('-a', '--add-user', action="store", dest='user', type=unicode, help='Add a user to the DB')
    args = parser.parse_args()
    if args.user:
        r = connect_redis()
        user = args.user.split(':')
        user[2] = dns.name.from_unicode(user[2])
        add_user(*user, r=r)
        sys.exit(0)
        pass

    if args.background:
        with daemon.DaemonContext():
            gevent.reinit()
            serve(args.zone)
            pass
        pass
    else:
        serve(args.zone)
        pass
    pass
