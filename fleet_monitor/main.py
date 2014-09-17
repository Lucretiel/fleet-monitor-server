import asyncio
import websockets
from collections import namedtuple
import argparse
import json


EntityType = namedtuple('EntityType', ('type', 'cmd', 'fields'))

#TODO: separate table columns in the dashboard from fields names for fleetctl
#TODO: Find a better way to handle different versions of fleet
#TODO: command line verbosity control
#TODO: find a way to merge the list-units and list-unit-files data
unit = EntityType('unit', 'list-units', (
    'unit',
    'load',
    'active',
    'sub',
    'machine',
    #'state',
    #'dstate',
    #'desc',
    #'tmachine',
    #'hash'
    ))

machine = EntityType('machine', 'list-machines', (
    'machine',
    'ip',
    'metadata'))


@asyncio.coroutine
def generic_scanner(entity, frequency, fleetctl_args, update_callback):
    '''
    Coroutine to perform the fleetctl polling. Repeatedly calls fleetctl every
    `frequency` seconds, using `fleetctl_args`, which should have a path to
    fleetctl as well as extra arguments, assembles the results into
    json, and calls `update_callback` with it. Raises a RuntimeError if the
    command fails.
    '''

    entity_type, entity_cmd, entity_fields = entity

    print("Launched {} scanner".format(entity_type))

    # assemble the command
    cmd = fleetctl_args + (
        entity_cmd, '-l', '-no-legend', '-fields',
        ','.join(entity_fields))

    # Create a template JSON object
    message = {
        'type': entity_type,
        'fields': entity_fields,
        'items': []
    }

    while True:
        # Launch a fleetctl process
        process = yield from asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        # Retreive data from the process
        data, error = yield from process.communicate()

        if process.returncode:
            print(
                "Error: {type} scanner failed with error code {code}\n"
                "Command: {cmd}\n"
                "Message:\n{msg}".format(
                    type=entity_type, code=process.returncode,
                    cmd=cmd, msg=error.decode()))
            return

        data = data.decode()

        # Create an update json and send it to the callback
        message['items'] = [line.split() for line in data.splitlines()]
        update_callback(json.dumps(message, separators=(',', ':')))

        yield from asyncio.sleep(frequency)


class WebsocketHandler:
    def __init__(self):
        print("Created websocket handler")
        self.queues = set()

    @asyncio.coroutine
    def connection(self, socket, path):
        '''
        Connection coroutine. Creates a queue on which to receive updates, and
        sends items on the queue to the socket. Exits when the connection is
        closed.
        '''

        #Create and add a message queue
        queue = asyncio.Queue()
        self.queues.add(queue)

        print('Websocket connected: "{}"'.format(path))

        try:
            while socket.open:
                data = yield from queue.get()
                yield from socket.send(data)

        except websockets.exceptions.InvalidState:
            pass

        finally:
            print('Websocket disconnected: "{}"'.format(path))
            self.queues.discard(queue)

    def update(self, entity_data):
        '''
        Callback called by the entity scanner to queue up updates for the
        clients
        '''
        for queue in self.queues:
            queue.put_nowait(entity_data)

    @asyncio.coroutine
    def serve(self, port, host='0.0.0.0'):
        '''
        Coroutine to create a websocket server
        '''
        yield from websockets.serve(self.connection, host, port)
        print('Serving websocket server at "ws://{}:{}"'.format(host, port))

###########################
# ARGUMENTS
###########################

parser = argparse.ArgumentParser()

# Add normal arguments
arg = parser.add_argument
arg('-m', '--machine-freq', type=int, default=10,
    help="Frequency in seconds of list-machines polling")
arg('-u', '--unit-freq', type=int, default=2,
    help="Frequency in seconds of list-units polling")
arg('-p', '--port', type=int, default=8989)
arg('-c', '--fleetctl', default='fleetctl',
    help="Path to the fleetctl binary")
arg('--endpoint-port', default=4001, type=int)
arg('--tunnel-port', default=22, type=int)

# Add mutually exclusive endpoint arguments (normal or ssh)
arg = parser.add_mutually_exclusive_group().add_argument
arg('-e', '--endpoint', help='Remote host to poll with fleetctl')
arg('-t', '--tunnel', help='Remote host to connect to with ssh tunnel')


def main(argv):
    args = parser.parse_args(argv[1:])

    # If we're using a tunnel or endpoint, add it to the command line arguments
    def fleetctl_args():
        yield args.fleetctl
        if args.endpoint:
            yield '--endpoint'
            yield 'http://{}:{}'.format(args.endpoint, args.endpoint_port)
        elif args.tunnel:
            yield '--tunnel'
            yield '{}:{}'.format(args.tunnel, args.tunnel_port)

    fleetctl_args = tuple(fleetctl_args())

    # Create socket manager
    socket_handler = WebsocketHandler()

    # Create task coroutines
    tasks = [
        # Unit scanning coroutine
        generic_scanner(
            unit,
            args.unit_freq,
            fleetctl_args,
            socket_handler.update),

        # Machine scanning coroutine
        generic_scanner(
            machine,
            args.machine_freq,
            fleetctl_args,
            socket_handler.update)]

    loop = asyncio.get_event_loop()

    # Spawn the server
    #TODO: check if this fails (for instance, the port is already in use
    asyncio.async(socket_handler.serve(args.port))

    # Spawn the scanners. Stop when either one fails.
    loop.run_until_complete(asyncio.wait(
        tasks, return_when=asyncio.FIRST_COMPLETED))


if __name__ == '__main__':
    from sys import argv
    main(argv)
