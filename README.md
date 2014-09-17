fleet-monitor-server
====================

Server for monitoring fleet. Pairs with fleet-monitor-dashboard.

Getting Started
---------------

This project requires Python 3.4, the python websockets module (`pip install -r requirements.txt`), and a local fleetctl binary. To launch the server, run `python3.4 -m fleet_monitor.main <args>` from the project root directory. 

Usage
-----

- `-h`: Print usage message and exit
- `-p <port>`: Port on which to host the websocket server. Defaults to 8989
- `-c <cmd>`: Path to the fleetctl command. Defaults to `fleetctl`, searching your current `$PATH`
- `-m <seconds>`: Frequency in seconds to poll for machine data. Defaults to 10
- `-u <seconds>`: Frequency in seconds to poll for unit data. Defaults to 2
- `-e <host>`, `--endpoint-port <port>`: Sepecify an etcd host and port for fleetctl to connect to. This will normally be an etcd endpoint of the cluster; the port defaults to 4001.
- `-t <host>`, `--tunnel-port`: Specify an ssh host and port for fleetctl to tunnel to. The port defaults to 22.

Design
------

When run, the server creates a WebSockets server on the specified port (`-p`) (default 8989). Clients connected to this port receive published updates of machines and units in the fleetctl cluster. Currently, these updates are accumulated by periodically running `fleetctl list-units...` and `fleetctl list-machines...`, though when fleetctl releases and HTTP API that will be used instead.

Updates sent to the server are of the form:

```json
{
	"type": <machine|unit>,
	"fields": ["field1_name", "field2_name", ...],
	"items": [
		["item1_field1", "item2_field2", ...],
		["item2_field1", "item2_field2", ...],
		...
	]
}
```

Notes
-----

This is a very basic prototype, created in only a day or two. As such, I
haven't been able to do much code organization, write unit tests, or organize
the project into a standard python project (setup.py etc).

TODO
----

- **UNIT TESTS**
- Modularize- separate main, scanning, and websockets
- Modularize polling code, so that transitioning to fleet API is easier
- Add setup.py, .travisrc, other project stuff
- Create docker container
