from collections import deque

from ipc import bcast
from config import servers
from util import coroutine

@coroutine
def twophase(db):
    state = 'waiting'
    hnum = 0
    nreceives = 0
    client = None
    request_q = deque()

    while True:
        if len(request_q) > 0 and state == 'waiting':
            data, sock, addr = request_q.popleft()
        else:
            data, sock, addr = (yield)

        if 'request' in data:
            if state != 'waiting':
                request_q.append((data, sock, addr))
                continue
            # we have been chosen as the coordinator
            # we need to check with all acceptors
            print 'coordinator received request, preparing %s' % str(data)
            client = addr
            state = 'preparing'
            nreceives = 0
            prep_msg = json.dumps({'protocol':'2pc',
                                   'prepare':data['request'],
                                   'i':hnum + 1})
            bcast(sock, prep_msg)
        elif state == 'preparing':
            if 'promise' in data:
                nreceives += 1
                if nreceives == len(servers):
                    print 'got n promises, moving on'
                    state = 'accepting'
                    nreceives = 0
                    accept_msg = json.dumps({'protocol':'2pc',
                                             'accept':data['promise'],
                                             'i':hnum})
                    bcast(sock, accept_msg)
            elif 'nack' in data:
                state = 'waiting'
                nreceives = 0
        elif state == 'accepting':
            if 'accepted' in data:
                nreceives += 1
                if nreceives  == len(servers):
                    print 'successfully got n accepts'
                    success_msg = json.dumps({'protocol':'2pc',
                                              'success':True})
                    sock.sendto(success_msg, client)
                    state = 'waiting'
                    nreceives = 0
                    client = None
            elif 'nack' in data:
                state = 'waiting'
                nreceives = 0

        if 'prepare' in data:
            if data['i'] > hnum:
                hnum = data['i']
                response = json.dumps({'protocol':'2pc',
                                       'promise':data['prepare'],
                                       'i':data['i']})
            else:
                response = json.dumps({'protocol':'2pc',
                                       'nack':data['i']})
            sock.sendto(response, addr)
        elif 'accept' in data:
            if data['i'] == hnum:
                learner.send(data['accept'])
                response = json.dumps({'protocol':'2pc',
                                       'accepted':data['accept'],
                                       'i':hnum})
            else:
                response = json.dumps({'protocol':'2pc',
                                       'nack':data['i']})
            sock.sendto(response, addr)
