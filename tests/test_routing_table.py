# coding: utf-8
import unittest

from kademlia_aio import RoutingTable, get_identifier


class RoutingTableTests(unittest.TestCase):
    def test_construction(self):
        table = RoutingTable(0b0001)
        self.assertEqual(0b0001, table.node_identifier)
        self.assertEqual(20, table.k)
        self.assertEqual(160, len(table.buckets))
        self.assertEqual(160, len(table.replacement_caches))

    def test_distance(self):
        table = RoutingTable(0b0001)
        self.assertEqual(0b0000, table.distance(0b0001))
        self.assertEqual(0b0001, table.distance(0b0000))
        self.assertEqual(0b0011, table.distance(0b0010))
        self.assertEqual(0b0010, table.distance(0b0011))
        self.assertEqual(2**160-1 ^ 0b0001, table.distance(2**160-1))

    def test_bucket_index(self):
        table = RoutingTable(0b0001)
        self.assertEqual(160, table.bucket_index(0b0001)) # self
        self.assertEqual(159, table.bucket_index(0b0000))
        self.assertEqual(158, table.bucket_index(0b0010))
        self.assertEqual(158, table.bucket_index(0b0011))
        self.assertEqual(157, table.bucket_index(0b0110))
        self.assertEqual(140, table.bucket_index(2**20-1))
        self.assertEqual(139, table.bucket_index(2**20))
        self.assertEqual(139, table.bucket_index(2**21-1))
        self.assertEqual(138, table.bucket_index(2**21))
        self.assertEqual(  0, table.bucket_index(2**160-1))

        self.assertRaises(ValueError, table.bucket_index, -1)
        self.assertRaises(ValueError, table.bucket_index, 2**160)

    def test_update_peer_plenty_of_room(self):
        table = RoutingTable(0b0001)
        table.update_peer(0b0000, ('10.0.0.1', 12345))
        self.assertEqual(('10.0.0.1', 12345), table.buckets[159][0b0000])

        table.update_peer(0b0010, ('10.0.0.2', 12345))
        self.assertEqual(('10.0.0.1', 12345), table.buckets[159][0b0000])
        self.assertEqual(('10.0.0.2', 12345), table.buckets[158][0b0010])

    def test_update_peer_replace(self):
        table = RoutingTable(0b0001)
        table.update_peer(0b0000, ('10.0.0.1', 12345))
        self.assertEqual(('10.0.0.1', 12345), table.buckets[159][0b0000])

        table.update_peer(0b0000, ('10.0.0.2', 12345))
        self.assertEqual(('10.0.0.2', 12345), table.buckets[159][0b0000])

    def test_update_peer_move_to_end(self):
        table = RoutingTable(0b0111)
        two = 0b0010
        three = 0b0011

        self.assertEqual(157, table.bucket_index(two))
        self.assertEqual(157, table.bucket_index(three))

        bucket = table.buckets[157]

        table.update_peer(two, ('10.0.0.2', 12345))
        self.assertEqual(('10.0.0.2', 12345), bucket[two])

        table.update_peer(three, ('10.0.0.3', 12345))
        self.assertEqual(('10.0.0.3', 12345), bucket[three])

        self.assertEqual([two, three], list(bucket.keys()))

        table.update_peer(two, ('10.0.0.2', 12345))
        self.assertEqual(('10.0.0.2', 12345), bucket[two])
        self.assertEqual(('10.0.0.3', 12345), bucket[three])

        self.assertEqual([three, two], list(bucket.keys()))

    def test_full_bucket(self):
        table = RoutingTable(0b1111, k=5)
        one = 2**158 - 1
        two = 2**158 - 2
        three = 2**158 - 3
        four = 2**158 - 4
        five = 2**158 - 5
        six = 2**158 - 6

        bucket_index = 2

        for i in range(1, 7):
            self.assertEqual(bucket_index, table.bucket_index(2**158-i))

        bucket = table.buckets[bucket_index]
        replacement_cache = table.replacement_caches[bucket_index]

        table.update_peer(one, 'one')
        table.update_peer(two, 'two')
        table.update_peer(three, 'three')
        table.update_peer(four, 'four')
        table.update_peer(five, 'five')

        self.assertEqual(5, len(bucket))
        self.assertEqual([one, two, three, four, five], list(bucket.keys()))

        table.update_peer(six, 'six')
        self.assertEqual(5, len(bucket))
        self.assertEqual(1, len(replacement_cache))
        self.assertEqual('six', replacement_cache[six])

        table.update_peer(six, 'six-new')
        self.assertEqual(5, len(bucket))
        self.assertEqual(1, len(replacement_cache))
        self.assertEqual('six-new', replacement_cache[six])

    def test_replacing_peer(self):
        table = RoutingTable(0b1111, k=5)
        one = 2**158 - 1
        two = 2**158 - 2
        three = 2**158 - 3
        four = 2**158 - 4
        five = 2**158 - 5
        six = 2**158 - 6

        bucket_index = 2

        for i in range(1, 7):
            self.assertEqual(bucket_index, table.bucket_index(2**158-i))

        bucket = table.buckets[bucket_index]
        replacement_cache = table.replacement_caches[bucket_index]

        table.update_peer(one, 'one')
        table.update_peer(two, 'two')
        table.update_peer(three, 'three')
        table.update_peer(four, 'four')
        table.update_peer(five, 'five')
        table.update_peer(six, 'six')

        self.assertEqual(5, len(bucket))
        self.assertEqual(1, len(replacement_cache))
        self.assertEqual('six', replacement_cache[six])

        table.forget_peer(three)
        self.assertEqual(5, len(bucket))
        self.assertEqual(0, len(replacement_cache))
        self.assertEqual('six', bucket[six])

    def test_finding_peers(self):
        table = RoutingTable(0b0000, k=5)

        table.update_peer(0b0001, 'one')
        table.update_peer(0b0010, 'two')
        table.update_peer(0b0011, 'three')
        table.update_peer(0b0100, 'four')
        # 0b0101 (five) is the key we're looking for
        table.update_peer(0b0110, 'six')
        table.update_peer(0b0111, 'seven')
        table.update_peer(0b1000, 'eight')
        table.update_peer(0b1001, 'nine')

        self.assertEqual([
            (0b0111, 'seven'),
            (0b0110, 'six'),
            (0b0100, 'four'),
            (0b0011, 'three'),
            (0b0010, 'two'),
        ], list(table.find_closest_peers(0b0101)))

        self.assertEqual([
            (0b1001, 'nine'),
            (0b1000, 'eight'),
            (0b0111, 'seven'),
            (0b0110, 'six'),
            (0b0100, 'four'),
        ], list(table.find_closest_peers(2**160-1)))
