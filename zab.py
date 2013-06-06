"""
    Zab - a fifo atomic broadcast protocol for replication.
        swaps epochs with peers to determine leader
        2-phase-commit for consensus on leaders and updates
"""
from time import time

from ipc import bcast
from config import servers
from util import coroutine

@coroutine
def zab(db):
    state = 'election'
    # epoch is (latest update number, time)
    epoch = (0, time())
    nreceives = 0
    client = None

    while True:
        data, sock, addr = (yield)
        
        if state == 'following':
            pass
        elif state == 'leading':
            pass
        elif state == 'election':
            # ask everyone for (state, epoch)
            pass

        if 'cepoch' in data:
            pass
        elif 'newepoch' in data:
            pass
        elif 'ack-e' in data:
            pass
        elif 'newleader' in data:
            pass
        elif 'ack-ld' in data:
            pass
        elif 'commit-ld' in data:
            pass
        elif 'propose' in data:
            pass
        elif 'ack' in data:
            pass
        elif 'commit' in data:
            pass
