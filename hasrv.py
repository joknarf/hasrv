#!/usr/bin/python
# hasrv.py
# Author: FJO
#
# automatic fallback and load balance to alive server
# from client side.
# get a server from list where we can connect to a port
#
# srv=$(hasrv.py -P 'srv1 srv2' -s 'backupsrv1 backupsrv2' -p 80)
# load balance between srv1 srv2 from clients IP 
# fallback to backupsrv1/2
#
# srv=$(hasrv.py -r -s 'srv-ha' -p 80)
# with multiple IN A adddresses for a hostname, load balance
# and fallback to the different reverse hostnames of 
# the IPs
#

import socket, struct, sys, os, argparse
try:
    import configparser
except:
    import ConfigParser
from logging import error, warning, info, basicConfig, DEBUG
from multiprocessing import Process, Queue, Pool
from random import shuffle

class Hasrv():
    def __init__(self, primaries, servers, port, timeout=3, resolve=False):
        self.primaries = primaries
        self.servers = servers
        self.port = port
        self.timeout = timeout
        if resolve:
            self.servers = self.resolve_names(servers)
            self.primaries = self.resolve_names(primaries)
        if self.primaries:
            if len(self.primaries) == 1:
                self.primary = self.primaries[0]
            else:
                self.auto_primary(self.primaries)
                self.primaries.remove(self.primary)
                self.servers = self.primaries + [ i for i in self.servers if i not in self.primaries ]
        else:
            self.auto_primary(self.servers)

    def auto_primary(self, primaries):
        ip = socket.gethostbyname(socket.gethostname())
        ipint = struct.unpack("!L", socket.inet_aton(ip))[0]
        self.primary = primaries[ipint%len(primaries)]
        
    def connect(self, server, port, timeout):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect((server,port))
        except socket.error, msg:
            warning("connect " + server + " on port " + str(port) + ": " + str(msg))
            sock.close()
            return False
        info("connect " + server + " on port "+ str(port) +": OK")
        sock.close()
        return True

    def name2ips(self, server):
        try:
            infos = socket.getaddrinfo(server, self.port)
        except:
            warning('cannot resolve ' + server)
            infos = []
        ips = []
        for info in infos:
            if info[0] == socket.AF_INET and info[1] == socket.SOCK_STREAM:
                ips.append(info[4][0])
        return ips

    def ip2name(self, addr):
        try:
            infos = socket.gethostbyaddr(addr)
        except:
            warning('cannot resolve ' + addr)
            infos = [ addr ]
        return infos[0]
        
    def resolve_names(self, names):
        resolved = []
        for name in names:
            for ip in self.name2ips(name):
                resolved.append(self.ip2name(ip))
        return resolved

    def get_alive(self):
        if self.connect(self.primary, self.port, self.timeout):
            return self.primary
        for server in self.servers:
            if server == self.primary:
                continue
            if self.connect(server, self.port, self.timeout):
                return server
        warning("cannot connect to any server on port " + str(self.port))
        return None

    def child_connect(self, q, server):
        if self.connect(server, self.port, self.timeout):
           q.put(server)

    def multi_connect(self, servers):
         q = Queue()
         processes = []
         shuffle(servers)
         for server in servers:
           p = Process(target=self.child_connect, args=(q, server))
           p.start()
           processes.append(p)
         try:
             server = q.get(True, self.timeout+1)
         except:
             server = None
         for p in processes:
             p.terminate() 
         return server
     
    def get_first_alive(self):
        server = None
        if self.primaries:
            server = self.multi_connect(self.primaries)
            if server:
                return server
        if self.servers:
            server = self.multi_connect(self.servers)
        return server
        

def str2bool(str):
    return False if str in ['False','false','0'] else True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--primaries',  '-P', default='')
    parser.add_argument('--servers',    '-s', default='' )
    parser.add_argument('--port',       '-p', type=int, default=0)
    parser.add_argument('--timeout',    '-t', type=int, default=0)
    parser.add_argument('--resolve',    '-r', action='store_true')
    parser.add_argument('--first',      '-f', action='store_true')
    parser.add_argument('--config',     '-c')
    parser.add_argument('--configfile', '-C', default='/etc/hasrv.conf')
    parser.add_argument('--verbose',    '-v', action='store_true')
    args = parser.parse_args()
    options = vars(args).copy()
    options = {k:str(v) for (k,v) in options.items()}
    try:
        config = configparser.ConfigParser(options, allow_no_calue=True)
    except:
        config = ConfigParser.ConfigParser(options, allow_no_value=True)
    config.read([args.configfile, sys.path[0]+'/hasrv.conf', os.path.expanduser('~/.hasrv.conf')])
    section = args.config
    if not section:
        section = 'noconf'
    if section not in config.sections():
        if section != 'noconf':
            warning('cannot find section "' + section + '" in config file ' + args.configfile)
        config.add_section(section)
    options = {k:v for (k,v) in options.items() if v not in ['', '0','None','False']}
    primaries = config.get(section, 'primaries', 0, options).split()
    backups   = config.get(section, 'servers', 0, options).split("\n")
    port      = int(config.get(section, 'port', 0, options))
    if port == 0:
        warning('port is required')
        sys.exit(1)
    timeout   = int(config.get(section, 'timeout', 0, options))
    timeout   = 3 if timeout==0 else timeout
    resolve   = str2bool(config.get(section, 'resolve', 0, options)) 
    first     = str2bool(config.get(section, 'first',   0, options))
    verbose   = str2bool(config.get(section, 'verbose', 0, options))
    if verbose:
        basicConfig(level=DEBUG)
    servers   = []
    if len(backups) == 1:
        servers = backups[0].split()
    else: # multiple list of servers find the list containing primary
        if not primaries:
            servers = config.get(section, 'servers').split()
        for b in backups:
            s = b.split()
            if [p for p in primaries if p in s]:
                servers = s
                break
    if first:
        hasrv=Hasrv(primaries, servers, port, timeout=timeout,resolve=resolve).get_first_alive()
    else:
        hasrv=Hasrv(primaries, servers, port, timeout=timeout,resolve=resolve).get_alive()
    if hasrv:
        print(hasrv)
        sys.exit(0)
    sys.exit(1)
          

if __name__ == '__main__':
    main()

