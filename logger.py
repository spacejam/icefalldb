from config import store_logfile
from config import paxos_logfile
from config import loglevel

red = '\033[31m'
blue = '\033[92m'
yellow = '\033[37m'
end = '\033[0m'

def log_fail(msg):
    print red, msg, end

def log_warn(msg):
    if loglevel > 0:
        print yellow, msg, end

def log_info(msg):
    if loglevel > 1:
        print msg

def log_verbose(msg):
    if loglevel > 2:
        print blue, msg, end

