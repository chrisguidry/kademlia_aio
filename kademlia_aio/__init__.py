import asyncio
from collections import OrderedDict
from functools import wraps
import hashlib
import logging
import pickle
import random
import socket


logger = logging.getLogger(__name__)


def remote(func):
    '''
    Indicates that this instance method defines a remote procedure call (RPC).  All
    RPCs must be instance methods on a DatagramRPCProtocol subclass, and must
    include at least one positional argument to accept the connecting peer, a tuple
    of (ip, port).

    Applying this decorator converts the given instance method to a remote RPC
    request, while storing the original implementation as the function to invoke
    to reply to that call.
    '''
    @asyncio.coroutine
    @wraps(func)
    def inner(*args, **kwargs):
        instance, peer, *args = args
        answer = yield from instance.request(peer, inner.remote_name, *args, **kwargs)
        return answer
    inner.remote_name = func.__name__
    inner.reply_function = func
    return inner

class DatagramRPCProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.outstanding_requests = {}
        self.reply_functions = self.find_reply_functions()
        super(DatagramRPCProtocol, self).__init__()

    def find_reply_functions(self):
        '''Locates the reply functions (decorated by @remote) for all RPC methods,
           returning a dictionary mapping {RPC method name: reply function}.'''
        return {func.remote_name: func.reply_function
                for func in self.__class__.__dict__.values()
                if hasattr(func, 'remote_name')}

    def connection_made(self, transport):
        logger.info('connection_made: %r', transport)
        self.transport = transport

    def connection_lost(self, exception):
        logger.info('connection_lost: %r', exception)

    def error_received(self, exception):
        logger.info('error_received: %r', exception)

    def datagram_received(self, data, peer):
        logger.info('data_received: %r, %r', peer, data)
        direction, message_identifier, *details = pickle.loads(data)
        if direction == 'request':
            procedure_name, args, kwargs = details
            self.request_received(peer, message_identifier, procedure_name, args, kwargs)
        elif direction == 'reply':
            answer, = details
            self.reply_received(peer, message_identifier, answer)

    def request_received(self, peer, message_identifier, procedure_name, args, kwargs):
        logger.info('request from %r: %r(*%r, **%r) as message %r',
                    peer, procedure_name, args, kwargs, message_identifier)
        reply_function = self.reply_functions[procedure_name]
        answer = reply_function(self, peer, *args, **kwargs)
        self.reply(peer, message_identifier, answer)

    def reply_received(self, peer, message_identifier, answer):
        logger.info('reply to message %r, answer %r', message_identifier, answer)
        if message_identifier in self.outstanding_requests:
            reply = self.outstanding_requests.pop(message_identifier)
            reply.set_result(answer)

    def reply_timed_out(self, message_identifier):
        if message_identifier in self.outstanding_requests:
            reply = self.outstanding_requests.pop(message_identifier)
            reply.set_exception(socket.timeout)

    def request(self, peer, procedure_name, *args, **kwargs):
        message_identifier = get_random_identifier()
        reply = asyncio.Future()
        self.outstanding_requests[message_identifier] = reply

        loop = asyncio.get_event_loop()
        loop.call_later(5, self.reply_timed_out, message_identifier)

        message = pickle.dumps(('request', message_identifier, procedure_name, args, kwargs))
        self.transport.sendto(message, peer)

        return reply

    def reply(self, peer, message_identifier, answer):
        message = pickle.dumps(('reply', message_identifier, answer))
        self.transport.sendto(message, peer)


class KademliaNode(DatagramRPCProtocol):
    def __init__(self):
        self.identifier = get_random_identifier()
        self.routing_table = RoutingTable(self.identifier)
        self.storage = {}
        super(KademliaNode, self).__init__()

    def request_received(self, peer, message_identifier, procedure_name, args, kwargs):
        peer_identifier = args[0]
        self.routing_table.update_peer(peer_identifier, peer)
        super(KademliaNode, self).request_received(peer, message_identifier, procedure_name, args, kwargs)

    def reply_received(self, peer, message_identifier, answer):
        peer_identifier, answer = answer
        self.routing_table.update_peer(peer_identifier, peer)
        super(KademliaNode, self).reply_received(peer, message_identifier, answer)

    @remote
    def ping(self, peer, peer_identifier):
        logger.info('ping(%r, %r)', peer, peer_identifier)
        return (self.identifier, self.identifier)

    @remote
    def store(self, peer, peer_identifier, key, value):
        logger.info('store(%r, %r, %r, %r)', peer, peer_identifier, key, value)
        self.storage[key] = value
        return (self.identifier, True)

    @remote
    def find_node(self, peer, peer_identifier, key):
        logger.info('find_node(%r, %r, %r)', peer, peer_identifier, key)
        raise NotImplementedError()

    @remote
    def find_value(self, peer, peer_identifier, key):
        logger.info('find_value(%r, %r, %r)', peer, peer_identifier, key)
        if key in self.storage:
            return (self.identifier, self.storage[key])
        raise NotImplementedError()


class RoutingTable(object):
    def __init__(self, node_identifier, k=20):
        self.node_identifier = node_identifier
        self.k = k
        self.buckets = [OrderedDict() for _ in range(160)]
        self.replacement_caches = [OrderedDict() for _ in range(160)]
        super(RoutingTable, self).__init__()

    def distance(self, peer_identifier):
        return self.node_identifier ^ peer_identifier

    def bucket_index(self, peer_identifier):
        if not (0 <= peer_identifier < 2**160):
            raise ValueError('peer_identifier should be a number between 0 and 2*160-1.')
        return 160 - self.distance(peer_identifier).bit_length()

    def update_peer(self, peer_identifier, peer):
        bucket_index = self.bucket_index(peer_identifier)
        bucket = self.buckets[bucket_index]
        if peer_identifier in bucket:
            del bucket[peer_identifier]
            bucket[peer_identifier] = peer
        elif len(bucket) < self.k:
            bucket[peer_identifier] = peer
        else:
            replacement_cache = self.replacement_caches[bucket_index]
            if peer_identifier in replacement_cache:
                del replacement_cache[peer_identifier]
            replacement_cache[peer_identifier] = peer


def get_identifier(key):
    if hasattr(key, 'encode'):
        key = key.encode()
    digest = hashlib.sha1(key).digest()
    return int.from_bytes(digest, byteorder='big', signed=False)

def get_random_identifier():
    identifier = random.getrandbits(160)
    return get_identifier(identifier.to_bytes(20, byteorder='big', signed=False))

def logging_to_console():
    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(stream_handler)
