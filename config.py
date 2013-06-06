import ConfigParser

config = ConfigParser.RawConfigParser()
config.read('icefall.cfg')

store_path = config.get('datastore', 'location')
store_logfile = config.get('datastore', 'logfile')

paxos_acceptors = config.getint('paxos', 'acceptors')
paxos_learners = config.getint('paxos', 'learners')
paxos_leader_lease_time = config.getint('paxos', 'leader_lease_time')
paxos_logfile = config.get('paxos', 'logfile')

# 3 logs verbose info and higher priority
# 2 logs info and higher priority
# 1 logs warnings and higher priority
# 0 logs failures only
loglevel = 3

servers = [
            ('localhost', 5200),
            ('localhost', 5201),
            ('localhost', 5202),
            ('localhost', 5203),
            ('localhost', 5204),
          ]
