from collections import deque
import json

from config import servers
from ipc import bcast
from util import coroutine
from logger import log_fail
from logger import log_warn
from logger import log_info
from logger import log_verbose


@coroutine
def learner(db):
    while True:
        command = (yield)
        try:
            if command['action'] == 'put':
                log_info("setting db['%s'] to %s" % (command['key'], 
                                                     command['value']))
                db[command['key']] = command['value']
            elif command['action'] == 'incr':
                db[command['key']] = str(int(db[command['key']]) + 1)
                log_info("incrementing db['%s']" % command['key'])
            elif command['action'] == 'get':
                #TODO only needs to execute on one
                log_fail("db['%s'] is %s" % (command['key'],
                                             db[command['key']]))
        except KeyError:
            log_fail("key %s is not in db" % command['key'])

@coroutine
def paxos(learner):
    state = 'waiting'
    hnum = 0
    nreceives = 0
    client = None
    request_q = deque()
    current_i = None

    while True:
        if len(request_q) > 0 and state == 'waiting':
            # adds fifo semantics to system
            data, sock, addr = request_q.popleft()
        else:
            data, sock, addr = (yield)

        if 'request' in data:
            if state != 'waiting':
                request_q.append((data, sock, addr))
                log_warn('queue contains %s elements' % len(request_q))
                continue
            # we have been chosen as the proposer
            # we need to check with all acceptors
            log_verbose('coordinator received request, preparing %s' % str(data))
            client = addr
            state = 'preparing'
            nreceives = 0
            current_i = hnum + 1
            prep_msg = json.dumps({'protocol':'paxos',
                                   'prepare':data['request'],
                                   'i':hnum + 1})
            bcast(sock, prep_msg)
        elif state == 'preparing':
            if 'promise' in data and data['i'] == current_i:
                nreceives += 1
                if nreceives > (len(servers) / 2):
                    log_verbose('got more than n/2 promises, moving on')
                    state = 'accepting'
                    nreceives = 0
                    accept_msg = json.dumps({'protocol':'paxos',
                                             'accept':data['promise'],
                                             'i':hnum})
                    bcast(sock, accept_msg)
            elif 'nack' in data and data['i'] != current_i:
                log_warn('caught (and ignored) old nack: %s\tcurrent i: %s' % (data['i'], current_i))
            elif 'nack' in data and data['i'] == current_i:
                log_warn('falling back to waiting state from preparing')
                log_fail('nack id: %s\thnum: %s' % (data['i'], hnum))
                state = 'waiting'
                nreceives = 0
        elif state == 'accepting':
            if 'accepted' in data and data['i'] == current_i:
                nreceives += 1
                if nreceives > (len(servers) / 2):
                    log_verbose('successfully got more than n/2 accepts')
                    success_msg = json.dumps({'protocol':'paxos',
                                              'success':True})
                    sock.sendto(success_msg, client)
                    state = 'waiting'
                    nreceives = 0
                    current_i = None
                    client = None
            elif 'nack' in data and data['i'] != current_i:
                log_warn('caught (and ignored) old nack: %s\tcurrent i: %s' % (data['i'], current_i))
            elif 'nack' in data and data['i'] == current_i:
                log_warn('falling back to waiting state from accepting')
                log_fail('possible inconsistency')
                log_fail('nack id: %s\thnum: %s' % (data['i'], hnum))
                state = 'waiting'
                nreceives = 0

        if 'prepare' in data:
            if data['i'] > hnum:
                hnum = data['i']
                response = json.dumps({'protocol':'paxos',
                                       'promise':data['prepare'],
                                       'i':data['i']})
            else:
                log_warn('got prepare for number less than hnum')
                response = json.dumps({'protocol':'paxos',
                                       'nack':data['i']})
            sock.sendto(response, addr)
        elif 'accept' in data:
            if data['i'] == hnum:
                learner.send(data['accept'])
                response = json.dumps({'protocol':'paxos',
                                       'accepted':data['accept'],
                                       'i':hnum})
            else:
                log_warn('got accept for number other than hnum')
                log_fail('possible inconsistency')
                response = json.dumps({'protocol':'paxos',
                                       'nack':data['i']})
            sock.sendto(response, addr)
