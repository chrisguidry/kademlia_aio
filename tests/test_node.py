# coding: utf-8
import asyncio
from functools import wraps
import socket
import unittest

import mock

from kademlia_aio import KademliaNode, get_identifier


def async_unit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(func)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(coro(*args, **kwargs))
    return wrapper


class KademliaNodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_loop = asyncio.get_event_loop()
        cls.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.loop)

        cls.node1_address = ('127.0.0.1', 32001)
        future = cls.loop.create_datagram_endpoint(KademliaNode, local_addr=cls.node1_address)
        cls.transport1, cls.node1 = cls.loop.run_until_complete(future)

        cls.node2_address = ('127.0.0.1', 32002)
        future = cls.loop.create_datagram_endpoint(KademliaNode, local_addr=cls.node2_address)
        cls.transport2, cls.node2 = cls.loop.run_until_complete(future)

    def setUp(self):
        self.node1.reply_timeout = 1
        self.node2.reply_timeout = 1

    @classmethod
    def tearDownClass(cls):
        cls.loop.stop()
        asyncio.set_event_loop(cls.original_loop)

    @async_unit
    def test_timeout(self):
        try:
            self.node1.reply_timeout = 0.01
            yield from self.node1.ping(('127.0.0.1', 32003), self.node1.identifier)
            self.assertFalse(True, 'should have timed out') # pragma: no cover
        except socket.timeout:
            pass

    @async_unit
    def test_ping(self):
       reply = yield from self.node1.ping(self.node2_address, self.node1.identifier)
       self.assertEqual(reply, self.node2.identifier)

    @async_unit
    def test_store_and_find(self):
        key = get_identifier('hello')
        reply = yield from self.node1.store(self.node2_address, self.node1.identifier, key, 'world')
        self.assertTrue(reply)
        stored = yield from self.node1.find_value(self.node2_address, self.node1.identifier, key)
        self.assertEqual(('found', 'world'), stored)

    @async_unit
    def test_find_node(self):
        with mock.patch.object(self.node2.routing_table, 'find_closest_peers') as find_closest_peers:
            find_closest_peers.return_value = [(12345, ('127.0.0.2', 30000)), (12345, ('127.0.0.2', 30000))]
            key = get_identifier('hello')
            reply = yield from self.node1.find_node(self.node2_address, self.node1.identifier, key)
            self.assertEqual(find_closest_peers.return_value, reply)
            find_closest_peers.assert_called_once_with(key, excluding=self.node1.identifier)

    @async_unit
    def test_find_value_missing(self):
        with mock.patch.object(self.node2.routing_table, 'find_closest_peers') as find_closest_peers:
            find_closest_peers.return_value = [(12345, ('127.0.0.2', 30000)), (12345, ('127.0.0.2', 30000))]
            key = get_identifier('never_seen_this_one')
            reply = yield from self.node1.find_value(self.node2_address, self.node1.identifier, key)
            self.assertEqual(('notfound', find_closest_peers.return_value), reply)
            find_closest_peers.assert_called_once_with(key, excluding=self.node1.identifier)


class IterativeProceduresTests(unittest.TestCase):
    @async_unit
    def test_put(self):
        node = KademliaNode(identifier=1234)
        with mock.patch.object(node, 'lookup_node') as lookup_node, \
             mock.patch.object(node, 'store') as store:

            lookup_node.return_value = asyncio.Future()
            lookup_node.return_value.set_result([
                (1001, ('10.0.0.1', 1001)),
                (1002, ('10.0.0.2', 1002))
            ])

            store.return_value = asyncio.Future()
            store.return_value.set_result(True)

            result = yield from node.put('hello', 'world')
            self.assertTrue(result)

            lookup_node.assert_called_once_with(get_identifier('hello'), find_value=False)
            store.assert_has_calls([
                mock.call(('10.0.0.1', 1001), 1234, get_identifier('hello'), 'world'),
                mock.call(('10.0.0.2', 1002), 1234, get_identifier('hello'), 'world'),
            ])

    @async_unit
    def test_get(self):
        node = KademliaNode(identifier=1234)
        with mock.patch.object(node, 'lookup_node') as lookup_node:
            lookup_node.return_value = asyncio.Future()
            lookup_node.return_value.set_result('world')

            answer = yield from node.get('hello')
            self.assertEqual('world', answer)

            lookup_node.assert_called_once_with(get_identifier('hello'), find_value=True)

    @async_unit
    def test_get_shortcircuit(self):
        node = KademliaNode(identifier=1234)
        node.storage[get_identifier('hello')] = 'world'
        with mock.patch.object(node, 'lookup_node') as lookup_node:
            answer = yield from node.get('hello')
            self.assertEqual('world', answer)
            self.assertFalse(lookup_node.called)

    @async_unit
    def test_lookup_node_no_peers(self):
        node = KademliaNode()
        with mock.patch.object(node.routing_table, 'find_closest_peers') as find_closest_peers, \
             mock.patch.object(node, 'find_node') as find_node:
            find_closest_peers.return_value = []
            try:
                yield from node.lookup_node(1234, find_value=False)
                self.assertFalse(True, "should have timed out") # pragma: no cover
            except KeyError as e:
                self.assertIn('No peers available', str(e))

    @async_unit
    def test_lookup_node(self):
        node = KademliaNode(k=4, identifier=123)
        with mock.patch.object(node.routing_table, 'find_closest_peers') as find_closest_peers, \
             mock.patch.object(node, 'find_node') as find_node:

            find_closest_peers.return_value = [
                (1001, ('10.1.0.1', 1001)),
                (2001, ('10.2.0.1', 2001)),
            ]

            def local_find_node(peer, peer_identifier, key):
                connectivity = {
                    ('10.1.0.1', 1001): [
                        (1002, ('10.1.0.2', 1002)),
                        (1003, ('10.1.0.3', 1003)),
                        (123, ('127.0.0.1', 123))
                    ],
                    ('10.2.0.1', 2001): [
                        (2002, ('10.2.0.2', 2002)),
                        (2003, ('10.2.0.3', 2003))
                    ],
                    ('10.1.0.2', 1002): [
                        (1001, ('10.1.0.1', 1001)),
                        (2003, ('10.2.0.3', 2003))
                    ],
                    ('10.1.0.3', 1003): socket.timeout(),
                    ('10.2.0.2', 2002): [
                        (2001, ('10.2.0.1', 2001)),
                        (2003, ('10.2.0.3', 2003))
                    ],
                    ('10.2.0.3', 2003): [
                        (2001, ('10.2.0.1', 2001)),
                        (1001, ('10.1.0.1', 1001))
                    ]
                }
                future = asyncio.Future()
                result = connectivity[peer]
                if isinstance(result, socket.timeout):
                    future.set_exception(result)
                else:
                    future.set_result(result)
                return future
            find_node.side_effect = local_find_node

            other_contacts = yield from node.lookup_node(1500, find_value=False)
            self.assertEqual([
                (2001, ('10.2.0.1', 2001)),
                (2002, ('10.2.0.2', 2002)),
                (2003, ('10.2.0.3', 2003)),
                (1001, ('10.1.0.1', 1001))
            ], other_contacts)

            self.assertEqual(6, find_node.call_count)
            find_node.assert_has_calls([
                mock.call(('10.2.0.1', 2001), 123, 1500),
                mock.call(('10.1.0.1', 1001), 123, 1500),
                mock.call(('10.2.0.2', 2002), 123, 1500),
                mock.call(('10.2.0.3', 2003), 123, 1500),
                mock.call(('10.1.0.2', 1002), 123, 1500),
                mock.call(('10.1.0.3', 1003), 123, 1500)
            ])

    @async_unit
    def test_lookup_node_with_value(self):
        node = KademliaNode(k=4, identifier=123)
        with mock.patch.object(node.routing_table, 'find_closest_peers') as find_closest_peers, \
             mock.patch.object(node, 'find_value') as find_value:

            find_closest_peers.return_value = [
                (1001, ('10.1.0.1', 1001)),
                (2001, ('10.2.0.1', 2001)),
            ]

            def local_find_value(peer, peer_identifier, key):
                connectivity = {
                    ('10.1.0.1', 1001): ('notfound', [
                        (1002, ('10.1.0.2', 1002)),
                        (1003, ('10.1.0.3', 1003)),
                        (123, ('127.0.0.1', 123))
                    ]),
                    ('10.2.0.1', 2001): ('notfound', [
                        (2002, ('10.2.0.2', 2002)),
                        (2003, ('10.2.0.3', 2003))
                    ]),
                    ('10.1.0.2', 1002): ('notfound', [
                        (1001, ('10.1.0.1', 1001)),
                        (2003, ('10.2.0.3', 2003))
                    ]),
                    ('10.1.0.3', 1003): socket.timeout(),
                    ('10.2.0.2', 2002): ('found', 'world'),
                    ('10.2.0.3', 2003): ('notfound', [
                        (2001, ('10.2.0.1', 2001)),
                        (1001, ('10.1.0.1', 1001))
                    ])
                }
                future = asyncio.Future()
                future.set_result(connectivity[peer])
                return future
            find_value.side_effect = local_find_value

            other_contacts = yield from node.lookup_node(1500, find_value=True)
            self.assertEqual('world', other_contacts)

            self.assertEqual(3, find_value.call_count)
            find_value.assert_has_calls([
                mock.call(('10.2.0.1', 2001), 123, 1500),
                mock.call(('10.1.0.1', 1001), 123, 1500),
                mock.call(('10.2.0.2', 2002), 123, 1500)
            ])

    @async_unit
    def test_lookup_value_not_found(self):
        node = KademliaNode(k=4, identifier=123)
        with mock.patch.object(node.routing_table, 'find_closest_peers') as find_closest_peers, \
             mock.patch.object(node, 'find_value') as find_value:

            find_closest_peers.return_value = [
                (1001, ('10.1.0.1', 1001)),
                (2001, ('10.2.0.1', 2001)),
            ]

            def local_find_value(peer, peer_identifier, key):
                connectivity = {
                    ('10.1.0.1', 1001): ('notfound', [
                        (1002, ('10.1.0.2', 1002)),
                        (1003, ('10.1.0.3', 1003)),
                        (123, ('127.0.0.1', 123))
                    ]),
                    ('10.2.0.1', 2001): ('notfound', [
                        (2002, ('10.2.0.2', 2002)),
                        (2003, ('10.2.0.3', 2003))
                    ]),
                    ('10.1.0.2', 1002): ('notfound', [
                        (1001, ('10.1.0.1', 1001)),
                        (2003, ('10.2.0.3', 2003))
                    ]),
                    ('10.1.0.3', 1003): socket.timeout(),
                    ('10.2.0.2', 2002): ('notfound', [
                        (2001, ('10.2.0.1', 2001)),
                        (2003, ('10.2.0.3', 2003))
                    ]),
                    ('10.2.0.3', 2003): ('notfound', [
                        (2001, ('10.2.0.1', 2001)),
                        (1001, ('10.1.0.1', 1001))
                    ])
                }
                future = asyncio.Future()
                result = connectivity[peer]
                if isinstance(result, socket.timeout):
                    future.set_exception(result)
                else:
                    future.set_result(result)
                return future
            find_value.side_effect = local_find_value

            try:
                yield from node.lookup_node(1500, find_value=True)
                self.assertFalse(True, 'should have failed') # pragma: no cover
            except KeyError as e:
                self.assertIn('Not found among any available peers.', str(e))

            self.assertEqual(6, find_value.call_count)
            find_value.assert_has_calls([
                mock.call(('10.2.0.1', 2001), 123, 1500),
                mock.call(('10.1.0.1', 1001), 123, 1500),
                mock.call(('10.2.0.2', 2002), 123, 1500),
                mock.call(('10.2.0.3', 2003), 123, 1500),
                mock.call(('10.1.0.2', 1002), 123, 1500),
                mock.call(('10.1.0.3', 1003), 123, 1500)
            ])
