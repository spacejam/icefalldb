import sys
import socket

import simplejson as json

from config import servers
from logger import log_verbose
from logger import log_fail

def bcast(sock, msg):
    for s in servers:
        sock.sendto(msg, s)

def client(request):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    proposer = servers[1]
    s_request = request.split()
    if s_request[0] == 'get':
        request = {'action': 'get',
                   'key': s_request[1]}
    elif s_request[0] == 'incr':
        request = {'action': 'incr',
                   'key': s_request[1]}
    elif s_request[0] == 'put':
        request = {'action': 'put',
                   'key': s_request[1],
                   'value': s_request[2]}
    else:
        log_fail("bad command: %s" % request)
        sys.exit(-1)
    request_msg = json.dumps({'request':request, 'protocol':'paxos'})
    sock.sendto(request_msg, proposer)
    #log_verbose('cli waiting')
    #response, addr = sock.recvfrom(1024)
    #log_verbose('client got message: %s' % response)

def checksum(data):
    pass

def heartbeat():
    pass

def server(num):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(servers[num])
    while True:
        raw_data, addr = sock.recvfrom(1024)
        data = json.loads(raw_data)
        yield (data, sock, addr)

