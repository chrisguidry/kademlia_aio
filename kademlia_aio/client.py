import asyncio
import logging
import random
import signal
import socket
import sys

from kademlia_aio import KademliaNode, get_identifier, logging_to_console

logging_to_console()

logger = logging.getLogger(__name__)

loop = asyncio.get_event_loop()
loop.add_signal_handler(signal.SIGINT, loop.stop)

transport, node = loop.run_until_complete(loop.create_datagram_endpoint(KademliaNode, family=socket.SOCK_DGRAM))
logging.info('Pinging server....')

peers = [('127.0.0.1', int(p)) for p in sys.argv[1:]]

def ping_forever():
    while True:
        peer = random.choice(peers)
        try:
            peer_id = yield from node.ping(peer, node.identifier)
            yield from node.store(peer, node.identifier, get_identifier('hello'), 'world')
            stored = yield from node.find_value(peer, node.identifier, get_identifier('hello'))
            logger.info('%r from %r (%r)', stored, peer, peer_id)
            yield from asyncio.sleep(1)
        except socket.timeout:
            logger.info('Timeout from %r', peer)

asyncio.async(ping_forever())

loop.run_forever()
loop.close()
