import asyncio
import websockets
from collections import namedtuple
from contextlib import suppress
import argparse

unit_fields = (
    'state',
    'dstate',
    'desc',
    'machine',
    'tmachine',
    'unit',
    'load',
    'active',
    'sub',
    'hash')

machine_fields = (
    'machine',
    'ip',
    'metadata')


class Unit(namedtuple('Unit', unit_fields)):
    list_cmd = 'list-units'


class Machine(namedtuple('Machine', machine_fields)):
    list_cmd = 'list-machines'


@asyncio.coroutine
def generic_scanner(Entity, frequency, update_callback):
    '''
    Repeatedly scan for entities every `frequency` seconds, and publish them to
    the update_callback
    '''

    entity_type = Entity.__name__.lower()

    while True:
        # Launch a fleetctl process
        process = yield from asyncio.create_subprocess_exec(
            'fleetctl', Entity.list_cmd, '-l', '-no-legend',
            '-fields', ','.join(Entity._fields),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL)

        # Retreive data from the process
        data, _ = yield from process.communicate()

        # Create an update json and send it to the callback
        update_callback(json.dumps(
            {
                'type': entity_type,
                'items': [
                    vars(Entity(*line.split()))
                    for line in data.splitlines()]
            },
            separators=(',', ':')))

        yield from asyncio.sleep(frequency)


class WebsocketHandler:
    def __init__(self):
        self._sockets = set()

    @asyncio.coroutine
    def connection(self, socket, path):
        '''
        Connection coroutine. Creates a queue on which to receive updates, and
        sends items on the queue to the socket
        '''

        #Create and add a message queue
        queue = asyncio.Queue()
        self.sockets.add(queue)

        try:
            while socket.open:
                data = yield from queue.get()
                yield from socket.send(data)

        except websockets.exceptions.InvalidState:
            pass

        finally:
            self.sockets.discard(queue)

    def update(entity_data):
        '''
        Callback called by the entity scanner to queue up updates for the
        clients
        '''
        for queue in self.queues:
            queue.put_nowait(entity_data)

    @asyncio.coroutine
    def serve(self, port, host=None):
        '''
        Coroutine to create a websocket server
        '''
        return websockets.serve(self.connection, host, port)


def main(argv):
    parser = argparse.ArgumentParser()
    arg = parser.add_argument

    arg('-m', '--machine-freq', type=int, default=10, help=
        "Frequency in seconds of list-machines polling")
    arg('-f', '--unit-freq', type=int, default=2, help=
        "Frequency in seconds of list-units polling")
    arg('-p', '--port', type=int, default=8989)

    args = parser.parse_args(argv)

    socket_handler = WebsocketHandler()

    loop = asyncio.get_event_loop()

    loop.run_until_complete(asyncio.wait([
        generic_scanner(Unit, args.unit_freq, socket_handler.update),
        generic_scanner(Machine, args.machine_freq, socket_handler.update),
        socket_handler.serve]))
    loop.run_forever()


if __name__ == '__main__':
    from sys import argv
    main(argv)
