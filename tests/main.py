#!/usr/bin/env python
"""
Released into the public domain by Legoktm, 2013
"""

import unittest

import pywikibot
import sys
sys.argv.append('--memcache=127.0.0.1')  # Woot.
import wdapi


class TestAPI(unittest.TestCase):

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

if __name__ == "__main__":
    unittest.main()
