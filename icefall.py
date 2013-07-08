#!/usr/bin/env python
"""
    icefall - distributed database

    bully (lowest start epoch|host|pid) for election
    zab for serialization
    merkle trees for anti-entropy
    b+ for persistance
"""

import sys
from multiprocessing import Pool

from config import store_path
from paxos import paxos
from paxos import learner
from twophase import twophase
from zab import zab
#from heartbeat import heartbeat
#from election import election
#from sync import sync
from ipc import client
from ipc import server
import dbm

def driver(num):
    db = dbm.open("test%d" % num, 'c')
    learner_instance = learner(db)
    paxos_instance = paxos(learner_instance)
    twophase_instance = twophase(db)
    zab_instance = zab(db)
    #heartbeat_instance = heartbeat()
    #election_instance = election()
    #sync_instance = sync()

    s = server(num)
    for data, sock, addr in s:
        proto = data['protocol']
        if proto == 'paxos':
            paxos_instance.send((data, sock, addr))
        elif proto == '2pc':
            twophase_instance.send((data, sock, addr))
        elif proto == 'zab':
            zab.send((data, sock, addr))
        elif proto == 'election':
            pass
            #election_instance.send((data, sock, addr))
        elif proto == 'heartbeat':
            pass
            #heartbeat_instance.send((data, sock, addr))
        elif proto == 'sync':
            pass
            #sync_instance.send((data, sock, addr))
        else:
            pass


if __name__ == '__main__':
    from getopt import getopt, GetoptError
    
    try:
        opts, args = getopt(sys.argv[1:],"c:s")
    except GetoptError:
        print ('%s: [-c proposal] [-s]' % sys.argv[0])
        sys.exit(111)
    for opt, arg in opts:
        if opt == '-c':
            client(arg)
        elif opt == '-s':
            p = Pool(5)
            p.map(driver, [0,1,2,3,4])
        else:
            assert False, "unhandled option"

