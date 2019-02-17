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

import socket, struct, sys, argparse
from logging import warning, info

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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--primaries', '-P', default='')
    parser.add_argument('--servers', '-s' )
    parser.add_argument('--port', '-p', type=int)
    parser.add_argument('--resolve', '-r', action='store_true')
    args = parser.parse_args()
    primaries = args.primaries.split()
    backups = args.servers.split("\n")
    servers = []
    if len(backups) == 1:
        servers = backups[0].split()
    else: # multiple list of servers find the list containing primary
        for b in backups:
            s = b.split()
            if [p for p in primaries if p in s]:
                servers = s
                break
    hasrv=Hasrv(primaries, servers, args.port, resolve=args.resolve).get_alive()
    if hasrv:
        print(hasrv)
        sys.exit(0)
    sys.exit(1)
          

if __name__ == '__main__':
    main()

