#!/usr/bin/env python
"""
Released into the public domain by Legoktm, 2013
"""

import hashlib
import mwparserfromhell
import pywikibot
from pywikibot.data import api
import re
import redis
import sys


#normalize/shorten a few names
norm = {'target required claim': 'target',
        'one of': 'oneof',
        'single value': 'single',
        'unique value': 'unique',
        }


def get_mc_serv():
    serv = 'tools-redis'
    for arg in sys.argv:
        if arg.startswith('--memcache'):
            serv = arg[11:]
    return serv

mc = redis.StrictRedis(get_mc_serv())  # TODO: Make this configurable
expiry = 60 * 60 * 24  # One day


def normalize(name):
    # So lazy.
    return norm.get(name, name)


class WDProperty(pywikibot.PropertyPage):
    def md5(self):
        # Hopefully this is unique enough.
        return hashlib.md5('wdapi' + self.getID() + str(self.repo)).hexdigest()

    def get(self, force=False, fetch_text=True, cache=True, *args):
        # Realistically no one even wants the property info, and datatype is its own function.
        # Cache controls only saving as cache, not fetching from it
        if fetch_text:
            return_this = super(pywikibot.PropertyPage, self).get(force, *args)  # Do it cuz
        else:
            return_this = {}
        # Check that we don't already have it stored
        if not force and hasattr(self, '_constraints'):
            return return_this

        talk = self.toggleTalkPage()
        if not talk.exists():
            text = ''
        else:
            g = mc.get(self.md5())
            if g is not None:
                self._constraints = g
                return return_this
            else:
                text = talk.get()

        code = mwparserfromhell.parse(text)
        d = {}
        for temp in code.filter_templates(recursive=False):
            if temp.name.lower().startswith('constraint:'):
                nm = temp.name.lower()[11:]
                nm = normalize(nm)
                if nm == 'format':
                    value = unicode(temp.get('pattern').value)
                    d[nm] = pywikibot.removeDisabledParts(value, tags=['nowiki'])
                elif nm in ['target', 'item']:
                    d[nm] = {'property': unicode(temp.get('property').value),
                             }
                    if temp.has_param('item'):
                        d[nm]['item'] = unicode(temp.get('item').value)

                elif nm == 'oneof':
                    values = unicode(temp.get('values').value)
                    values = pywikibot.removeDisabledParts(values, tags=['comments'])
                    values = values.replace('{{Q|', '').replace('{{q|', '').replace('}}', '')
                    values = values.split(', ')
                    d[nm] = list()
                    for v in values:
                        d[nm].append('q' + v)

                elif nm == 'reciprocal':
                    d[nm] = unicode(temp.get('property').value)

                else:
                    d[nm] = ''  # Just set a key like the API does

        self._constraints = d
        if cache:
            mc.set(self.md5(), self._constraints, expiry)
        return return_this

    def constraints(self, force=False):
        if force or not hasattr(self, '_constraints'):
            self.get(force=force, fetch_text=False)
        return self._constraints


def canClaimBeAdded(item, claim, checkDupe=True):
    prop = WDProperty(item.repo, claim.getID())
    prop.get(fetch_text=False)
    if not hasattr(item, '_content'):
        # TODO: Not all constraints require fetching this, so it should be lazy
        item.get()
    if checkDupe:
        if prop.getID() in item.claims:
            for c in item.claims[prop.getID()]:
                if c.getTarget().getID() == claim.getTarget().getID():
                    return False, 'checkDupe'

    # Run through the various constraints
    if 'format' in prop.constraints() and prop.getType() == 'string':
        match = re.match(prop.constraints()['format'], claim.getTarget())
        if not match or match.group(0) != claim.getTarget():
            return False, 'format'
    if 'oneof' in prop.constraints() and prop.getType() == 'wikibase-item':
        if not claim.getTarget().getID() in prop.constraints()['oneof']:
            return False, 'oneof'
    if 'single' in prop.constraints():
        if claim.getID() in item.claims:
            return False, 'single'

    #TODO: target, unique, item, reciprocal
    #at this point nothing failed.
    return True, None


def createItem(page, dontactuallysave=False):
    summary = u'Importing from [[:w:{0}:{1}]]'.format(page.site.language(), page.title())
    gen = api.PropertyGenerator('langlinks', titles=page.title(), lllimit='max',
                                site=page.site,
                                )
    sitelinks = {}
    labels = {}
    for c in gen:
        if 'langlinks' in c:
            for b in c['langlinks']:
                link = {'site': page.site.dbName(),
                        'title': b['*'],
                        }
                label = {'language': b['lang'],
                         'value': b['*'],
                         }
                sitelinks[link['site']] = link
                labels[label['language']] = label
        #lets add the origin page
    sitelinks[page.site.dbName()] = {'site': page.site.dbName(),
                                     'title': page.title(),
                                     }
    labels[page.site.language()] = {'language': page.site.language(),
                                    'value': page.title(),
                                    }
    data = {'sitelinks': sitelinks,
            'labels': labels,
            }
    if dontactuallysave:
        return data
    repo = page.site.data_repository()
    result = repo.editEntity({}, data, bot=True, summary=summary)
    if 'success' in result and result['success'] == 1:
        return pywikibot.ItemPage(repo, result['entity']['id'])
    else:
        raise ValueError(unicode(result))  # TODO raise a better error here
