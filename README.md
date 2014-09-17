fleet-monitor-server
====================

Server for monitoring fleet. Pairs with fleet-monitor-dashboard.

Usage
-----

- `-h`: Print usage message and exit
- `-p`: Port on which to host the websocket server
- `-c`: Path to the fleetctl command
- `-m`: Frequency in seconds to poll for machine data
- `-u`: Frequency in seconds to poll for unit data
- `-e`, `--endpoint-port`: Sepecify an etcd host and port for fleetctl to
	connect to
- `-t`, `--tunnel-port`: Specify an ssh host and port for fleetctl to tunnel
	to.

Design
------

When run, the server creates a WebSockets server on the specified port (`-p`)
(default 8989). Clients connected to this port receive published updates of
machines and units in the fleetctl cluster. Currently, these updates are
accumulated by periodically running `fleetctl list-units...` and
`fleetctl list-machines...`, though when fleetctl releases and HTTP API that
will be used instead.

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
