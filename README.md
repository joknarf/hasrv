# hasrv

```
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
to be used to load balance to different servers
can replace haproxy which stays a spof in infrastructure

```shell
Example:
  # server=$(hasrv myhost 22 mybackup1 mybackup2)
  # ssh $server echo I can connect to this server on port 22

  # server=$(hasrv -auto 22 myserver1 mysserver2)
  # ssh $server echo Load balance clients between myserver1 and myserver2
```
