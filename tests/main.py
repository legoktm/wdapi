#!/usr/bin/env python
"""
Released into the public domain by Legoktm, 2013
"""

import unittest

import pywikibot

import wdapi


class TestAPI(unittest.TestCase):

    def setUp(self):
        self.repo = pywikibot.Site('test', 'wikidata').data_repository()

    def test_nonexistent_prop(self):
        p = wdapi.WDProperty(self.repo, 'p234234')
        p.get(fetch_text=False)
        self.assertEqual(p.constraints(), {})