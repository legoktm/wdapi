#!/usr/bin/env python
"""
Released into the public domain by Legoktm, 2013
"""

import mwparserfromhell
import pywikibot
from pywikibot.data import api
import re


#normalize/shorten a few names
norm = {'target required claim': 'target',
        'one of': 'oneof',
        'single value': 'single',
        'unique value': 'unique'
}


def normalize(name):
    # So lazy.
    return norm.get(name, name)


class WDProperty(pywikibot.PropertyPage):
    def get(self, force=False, *args):
        return_this = super(pywikibot.PropertyPage, self).get(force, *args)  # Do it cuz
        # Check that we don't already have it stored
        if not force and hasattr(self, '_constraints'):
            return return_this

        talk = self.toggleTalkPage()
        if talk.exists():
            text = talk.get()
        else:
            text = ''
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
                    values = values.replace('{{Q|', '').replace('}}', '')
                    values = values.split(', ')
                    d[nm] = list()
                    for v in values:
                        d[nm].append('q' + v)

                elif nm == 'reciprocal':
                    d[nm] = unicode(temp.get('property').value)

                else:
                    d[nm] = ''  # Just set a key like the API does

        self._constraints = d
        return return_this

    def constraints(self, force=False):
        if force or not hasattr(self, '_constraints'):
            self.get(force=force)
        return self._constraints


def canClaimBeAdded(item, claim, checkDupe=True):
    prop = WDProperty(item.repo, claim.getID())
    prop.get()
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
        if item.getID() in item.claims:
            return False, 'single'

    #TODO: target, unique, item, reciprocal
    #at this point nothing failed.
    return True, None


def createItem(page):
    summary = 'Importing from [[:w:{0}:{1}]]'.format(page.site.language(), page.title())
    gen = api.PropertyGenerator('langlinks', titles=page.title(), lllimit='max',
                                site=page.site,
                                )
    sitelinks = {}
    labels = {}
    for c in gen:
        if 'langlinks' in c:
            for b in c['langlinks']:
                link = {'site': b['lang'].replace('-', '_') + 'wiki',
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
    repo = page.site.data_repository()
    result = repo.editEntity({}, data, bot=True, summary=summary)
    if 'success' in result and result['success'] == 1:
        return pywikibot.ItemPage(repo, result['entity']['id'])
    else:
        raise ValueError(unicode(result))  # TODO raise a better error here
