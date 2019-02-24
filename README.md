# hasrv.py

client side load balancer and fallback to servers

hasrv.py can be used to load balance connexions and fallback connexions to alive servers.
hasrv.py tries to connect to servers on the port specified and returns a server name that is reachable on the port.

typically can be used to load balance and secure API calls to front-ends.

```shell
usage: hasrv.py [-h] [--primaries PRIMARIES] [--servers SERVERS] [--port PORT]
                [--timeout TIMEOUT] [--resolve] [--first] [--config CONFIG]
                [--configfile CONFIGFILE] [--verbose]

optional arguments:
  -h, --help            show this help message and exit
  --primaries PRIMARIES, -P PRIMARIES
  --servers SERVERS, -s SERVERS
  --port PORT, -p PORT
  --timeout TIMEOUT, -t TIMEOUT
  --resolve, -r
  --first, -f
  --config CONFIG, -c CONFIG
  --configfile CONFIGFILE, -C CONFIGFILE
  --verbose, -v
 ```

### fallbackup to a server if primary server not responding on a port

```shell
# hasrv.py --primaries server1.domain --servers server2.domain --port 80
 WARNING:root:connect server1.domain on port 22: timed out
 server2.domain
```

### load balance clients according to their IP, fallback to server

```shell
# hasrv.py --primaries 'server1.domain server2.domain' --servers server3.domain --port 80
```

will choose server1.domain or server2.domain based on IP of client  
fallback to other primary if primary chosen is not responding  
fallback to server3.domain if none of primaries is responding

### choose first server responding

```shell
# hasrv.py --first --servers 'server1.domain server2.domain server3.domain' --port 80
```

will try to connect to the 3 servers in parallel, the first responding is chosen

### use DNS multi host resolution to store cluster information

```shell
# host cluster1.domain
cluster1.domain has address 10.0.0.10
cluster1.domain has address 10.0.0.11
cluster1.domain has address 10.0.0.12

# host 10.0.0.10
10.0.0.10.in-addr.arpa domain name pointer server1.domain
# host 10.0.0.11
11.0.0.10.in-addr.arpa domain name pointer server2.domain
# host 10.0.0.12
12.0.0.10.in-addr.arpa domain name pointer server3.domain

# hasrv.py --resolve --servers cluster1.domain
server2.domain
```
will load balance and fallback between server1.domain server2.domain and server3.domain.  
can use a backup cluster with `--servers cluster2.domain`  
can choose `--first` if you want to get the first server responding  

### use configuration file

```ini
hasrv.conf:
[mycluster]
primaries=server1.domain server2.domain
servers=server3.domain server4.domain
port=80
first=true
```

```
# hasrv.py --config mycluster
server1.domain
```
configuration file is by default searched in :  
* hasrv.conf file in the directory of hasrv.py
* ~/.hasrv.conf
* /etc/hasrv.conf

### multiple fallback according to primary

```
hasrv.conf
[mycluster]
servers=server1.domain server2.domain
        server3.domain server4.domain
        
# hasrv.py --primaries server3.domain --config mycluster
WARNING:root:connect server3.domain on port 22: timed out
server4.domain
```
as server3.domain is on the line `server3.domain server4.domain` the server4.domain is the fallback for server3.domain

# hasrv

Simple client side load balancer and fallback to servers

```shell
usage: hasrv <host> <port> <backup1> <backup2> ...
       hasrv -auto <port> <backup1> <backup2> ...
```
returns `<host>` if can connect to `<host>:<port>`

if connection failed, returns first `<backup>`
that can be connected to `<backup>:<port>`

if a host has multiple ip will return the name pointing
to the reverse of ip that can connect

can be used to switch to a backup server if 
primary not available

with -auto will give a server according to client ip
to be used to load balance to different servers.  
can be used to replace haproxy which stays a spof in infrastructure

```shell
Example:
  # server=$(hasrv myhost 22 mybackup1 mybackup2)
  # ssh $server echo I can connect to this server on port 22

  # server=$(hasrv -auto 22 myserver1 mysserver2)
  # ssh $server echo Load balance clients between myserver1 and myserver2
```
