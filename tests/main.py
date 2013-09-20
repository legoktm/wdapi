#!/usr/bin/env python
"""
Released into the public domain by Legoktm, 2013
"""

import unittest

import redis
import pywikibot
import sys
sys.argv.append('--memcache=127.0.0.1')  # Woot.
import wdapi


class TestWDProperty(unittest.TestCase):

    def setUp(self):
        self.repo = pywikibot.Site('test', 'wikidata').data_repository()

    def test_nonexistent_prop(self):
        p = wdapi.WDProperty(self.repo, 'p234234')
        p.get(fetch_text=False)
        self.assertEqual(p.constraints(), {})

    def test_one_of(self):
        p = wdapi.WDProperty(self.repo, 'p11')
        p.get(fetch_text=False)
        self.assertIn('oneof', p.constraints())
        self.assertIn('q12345', p.constraints()['oneof'])

    def test_single_value(self):
        p = wdapi.WDProperty(self.repo, 'p11')
        p.get(fetch_text=False)
        self.assertIn('single', p.constraints())

    def test_unique_value(self):
        p = wdapi.WDProperty(self.repo, 'p11')
        p.get(fetch_text=False)
        self.assertIn('unique', p.constraints())


class TestAddClaim(unittest.TestCase):

    def setUp(self):
        self.repo = pywikibot.Site('wikidata', 'wikidata').data_repository()
        self.p107 = pywikibot.Claim(self.repo, 'p107')
        self.p107.setTarget(pywikibot.ItemPage(self.repo, 'q1'))
        self.q15 = pywikibot.ItemPage(self.repo, 'Q15')

    def test_one_of(self):
        ok, error = wdapi.canClaimBeAdded(self.q15, self.p107)
        self.assertFalse(ok)
        self.assertEqual(error, 'oneof')

    def test_duplicate(self):
        c = pywikibot.Claim(self.repo, 'p361')
        c.setTarget(pywikibot.ItemPage(self.repo, 'q2'))
        ok, error = wdapi.canClaimBeAdded(self.q15, c)
        self.assertFalse(ok)
        self.assertEqual(error, 'checkDupe')


class TestCache(unittest.TestCase):

    def setUp(self):
        self.repo = pywikibot.Site('wikidata', 'wikidata').data_repository()
        self.prop = wdapi.WDProperty(self.repo, 'p107')

    def test_memcached(self):
        mc = redis.StrictRedis(wdapi.get_mc_serv())
        mc.delete(self.prop.md5())  # Clear anything that might exist
        self.assertEqual(mc.get(self.prop.md5()), None)  # Ok, it doesn't exist
        self.prop.get()
        # redis stores stuff as strings, so wrap it in a str()
        self.assertEqual(mc.get(self.prop.md5()), str(self.prop.constraints()))
        # Now lets fake the data and make sure we get fake data back.
        mc.set(self.prop.md5(), 'alskdhfiudbnvw')
        del self.prop._constraints  # Force a read from memcache
        self.assertEqual(self.prop.constraints(), 'alskdhfiudbnvw')
        mc.delete(self.prop.md5())  # So we don't corrupt any real data





if __name__ == "__main__":
    unittest.main()
