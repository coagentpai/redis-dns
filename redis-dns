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
import urlparse
import json
import datetime

from gredis import get_redis
import records

class Missing_Zone(Exception):
    pass # END Class Missing_Zone

def dns_handler(s, peer, data, zone):
    request = dns.message.from_wire(data)
    reply = dns.message.make_response(request)
    reply.flags |= dns.flags.AA
    reply.flags &= ~dns.flags.RA
    # We only answer the first question
    q = request.question[0]
    name = q.name
    rdtype = q.rdtype
    if name == zone:
        if rdtype == dns.rdatatype.NS:
            ns_records = [records.NS(dns.name.from_unicode(target)) for target in get_redis().smembers('%s:NAMESERVERS' % zone)]
            reply.answer.append(dns.rrset.from_rdata(name, 1800, *ns_records))
            s.sendto(reply.to_wire(), peer)
            return
        pass

    if name.is_subdomain(zone):
        IP = get_redis().hget("NODE:%s" % name, 'A')
        TXT = get_redis().hget("NODE:%s" % name, 'TXT')
        IPV6 = get_redis().hget("NODE:%s" % name, 'AAAA')
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
        # Bad request? Should we reply? What would be the ID?
        pass

def valid_auth(username, password, domain):
    if not get_redis().hget('USER:%s' % username, 'password') == password:
        return False
    if not get_redis().sismember('DOMAIN:%s' % username, domain):
        return False
    return True

def add_user(username, password, domain):
    get_redis().hset('USER:%s' % username, 'password', password)
    get_redis().sadd('DOMAIN:%s' % username, domain)
    pass

def delete_user(username, password, domain):
    raw_domains = get_redis().smembers('DOMAIN:%s' % username)
    get_redis().delete('USER:%s' % username)
    for domain in [ dns.name.from_unicode(raw_domain) for raw_domain in raw_domains ]:
        get_redis().delete('NODE:%s', domain)
        pass
    get_redis().delete('DOMAIN:%s' % username)
    pass

def web_service_handler(env, start_response):
    def format_json(node):
        node_name = node.lstrip('NODE:')
        records = [{'type': key, 'value': value} for key, value in get_redis().hgetall(node).items() if key != 'UPDATED']
        return (node_name, {'records': records, 'updated':  get_redis().hget(node, 'UPDATED')})

    if env['PATH_INFO'] == '/info':
        records = get_redis().keys('NODE:*') 
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
            if not valid_auth(username, password, hostname):
                start_response('401 Not Authorized', [('Content-Type', 'text/plain')])
                return ['Not Authorized\n']
            ip = args['myip'].pop()
            get_redis().hmset('NODE:%s' % hostname, {'A': ip, 'UPDATED': datetime.datetime.utcnow().isoformat() + 'Z'})
            logging.info('Set %s to %s' % (hostname, ip)) 
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


def web_service(port):
    server = gevent.pywsgi.WSGIServer(('0.0.0.0', port), web_service_handler)
    server.start()
    pass

def serve(zone = None, port = 8080):
    if zone is None:
        zone = get_redis().get('ZONE')
        pass

    if zone is None:
        raise Missing_Zone('DNS zone not set')
        pass

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('0.0.0.0', 53))
    web_service(port)
    dns_zone = dns.name.from_unicode(unicode(zone))
    while True:
        data, peer = s.recvfrom(8192)
        dns_greenlet = gevent.spawn(dns_handler, s, peer, data, dns_zone) 
        dns_greenlet.link_exception(partial(dns_failure, s, peer, data))


if __name__ == '__main__':
    # Be a good Unix daemon
    import argparse
    import daemon

    parser = argparse.ArgumentParser(description='Greenlet dynamic DNS server')
    subparsers = parser.add_subparsers(help='The operation that you want to run on the server.')

    def users(args):
        domain = dns.name.from_unicode(args.domain)
        if args.add:
            add_user(args.username, args.password, domain)
            pass
        if args.delete:
            delete_user(args.username, args.password, domain)
            pass
        pass

    def zone(args):
        get_redis().set('ZONE', args.zone)
        get_redis().sadd('%s:NAMESERVERS' % args.zone, args.nameservers)
        pass

    def run(args):
        if args.background:
            with daemon.DaemonContext():
                gevent.reinit()
                serve(port=args.port)
                pass
            pass
        else:
            try:
                serve(port=args.port)
            except Missing_Zone as e:
                parser.error('No zone has been defined, try providing one or setting it with the zone sub-command.')
            pass
        pass
 
    # Users parser
    users_parser = subparsers.add_parser('users', help='Modifiy the configured users for the server.')
    users_parser.add_argument('-a', '--add-user', action="store_true", dest='add', help='Add a user to the service.')
    users_parser.add_argument('-d', '--delete-user', action="store_true", dest='delete', help='Delete a user from the service.')
    for arg in ('username', 'password', 'domain'):
        users_parser.add_argument(arg, type=unicode, nargs='?')
        pass
    users_parser.set_defaults(func=users)
    
    # Daemon parser 
    run_parser = subparsers.add_parser('run', help='Start the DNS server.')
    run_parser.add_argument('-b', '--background', dest='background', action='store_true', help='Background the server')
    run_parser.add_argument('-p', '--web-port', dest='port', default=8080, type=int, help='Port for the web service')
    run_parser.set_defaults(func=run)

    # Zone parser
    zone_parser = subparsers.add_parser('zone', help='Set the zone (domain) to serve')
    zone_parser.add_argument('zone', metavar='ZONE', type=unicode, help='Zone to serve (e.g. example.com)')
    zone_parser.add_argument('nameservers', metavar='NS', type=unicode, nargs='+', help='Nameservers to set for the zone (e.g. ns1.example.com)')
    zone_parser.set_defaults(func=zone)

    # Extract the args and then run the given action
    args = parser.parse_args()
    args.func(args)
    pass
