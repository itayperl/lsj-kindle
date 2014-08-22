#!/usr/bin/env python
# coding: utf-8
import glob
import gzip
import lxml.etree
import sys
import os
import codecs
import string
import argparse
import pickle
import re
import itertools
import unicodedata
from collections import defaultdict
from beta2unicode import beta2unicode

HEADER = u'''<!DOCTYPE html>
<html lang="el">
  <head>
    <meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>
    <title>Liddell &amp; Scott lexicon</title>
    <style type="text/css">
        .sense0 {}
        .sense1 {}
        .sense2 {
            margin-left: 1%;
        }
        .sense3 {
            margin-left: 2%;
        }
        .sense4 {
            margin-left: 3%;
        }
    </style>
  </head>
  <body>
  <mbp:frameset>
  <h3>Note</h3>
  <p>This E-book was generated from the following resources:</p>
  <ul>
      <li>Liddell &amp; Scott lexicon and greek morphology data from the <a href="http://www.perseus.tufts.edu">Perseus Digital Library</a>.
  </ul>
  <mbp:pagebreak />
'''

FOOTER = '''  </mbp:frameset>
  </body>
</html>
'''

def get_variations(word):
    def tonos(w):
        if w is None: return None
        # oxia => tonos
        try:
            variable = [ x for x in w if 'OXIA' in unicodedata.name(x) ]
        except:
            import pdb;pdb.set_trace()

        for v in variable:
            try:
                other = unicodedata.lookup(unicodedata.name(v).replace('OXIA', 'TONOS'))
                w = w.replace(v, other)
            except KeyError:
                pass
        return w

    def last_accent(w):
        if w is None: return None
        accented = [ (i, x) for i, x in enumerate(w) if ' WITH ' in unicodedata.name(x) ]
        if not len(accented):
            return

        last_idx, last_char = accented[-1]
        last_name = unicodedata.name(last_char)
        if 'OXIA' in last_name:
            last_reversed = last_name.replace('OXIA', 'VARIA')
            try:
                u = unicodedata.lookup(last_reversed)
            except KeyError:
                return

            w = list(w)
            w[last_idx] = u
            return u''.join(w)

        return

    for v in (word, tonos(word), last_accent(word), tonos(last_accent(word))):
        if v is not None:
            yield v

def get_text(sense):
    elt_text = lambda e: e.text or ''
    elt_tail = lambda e: e.tail or ''
    text = elt_text(sense)

    for e in sense.iterchildren():
        child_text = get_text(e)
        if e.get('lang') == 'greek':
            child_text = child_text.replace('&mdash;', u'\u2014')
            child_text = child_text.replace('&colon;', ':')
            # this is terrible. some entries have [greek] &equals; [numbers/fractions].
            parts = child_text.split('&equals;')
            conv = [ beta2unicode(p) if any(x in p for x in string.letters) else p for p in parts ]
            assert None not in conv, 'Invalid beta code %r' % (child_text)
            child_text = '='.join(conv)
        tail_text = elt_tail(e)
        if e.tag == 'tr':
            text += '<em>' + child_text + '</em>'
        elif e.tag == 'usg':
            text += '<strong>' + child_text + '</strong>'
        else:
            text += child_text
        text += tail_text

    return text

def write_entries(lsjfp, outfp, inflections):
    outfp.write(HEADER)
    p = lxml.etree.XMLParser(remove_blank_text=True, resolve_entities=False)
    tree = lxml.etree.parse(lsjfp, p)
    for entry in tree.getroot().xpath('//entry'):
        form = entry.find('form')
        if form is None:
            print lxml.etree.ElementTree(entry).write(sys.stdout)
        orth = form.find('orth')
        if orth is None:
            print lxml.etree.ElementTree(entry).write(sys.stdout)
        term = beta2unicode(orth.text)
        assert term is not None, orth.text

        outfp.write(u'    <idx:entry>\n')

        outfp.write(u'        <idx:orth>{}\n'.format(term.lower()))

        cur_infls = set(itertools.chain.from_iterable(get_variations(x) for x in inflections[term] | set([term])))
        cur_infls = sorted(cur_infls - set([term]))
        for chunk in (cur_infls[i:i+20] for i in range(0, len(cur_infls), 20)):
            outfp.write(u'            <idx:infl>\n')
            for infl in chunk:
                # stupid kindle strips quotes when searching a word.
                infl = infl.strip(u"'\u2019")
                outfp.write(u'                <idx:iform exact="yes" value="{}"  />\n'.format(infl))
            outfp.write(u'            </idx:infl>\n')
        outfp.write(u'        </idx:orth>\n')

        for sense in entry.iter('sense'):
            level = int(sense.get('level'))
            assert level in range(5)
            n = sense.get('n')
            prefix = '<strong>{}</strong> '.format(n) if level != 0 else ''
            outfp.write(u'            <div class="sense{}">{}{}</div>\n'.format(level, prefix, get_text(sense)))

        outfp.write(u'    </idx:entry>\n')
        outfp.write('    <mbp:pagebreak />\n')
    outfp.write(FOOTER)

def get_inflections(fp):
    d = defaultdict(set)

    xml = lxml.etree.parse(fp)
    for entry in xml.getroot().getchildren():
        def get(x):
            return entry.find(x).text
        beta = get('form') + get('lemma')
        if '^' in beta or '_' in beta:
            # skip weird stuff
            continue

        lemma = beta2unicode(get('lemma'))

        form = beta2unicode(get('form'))
        if None in (form, lemma):
            print 'bad beta {}'.format(get('form'))
            continue
        if form.endswith('\n'):
            import pdb;pdb.set_trace()
        d[lemma].add(form)
        
    return d

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('outfile', help='Output MOBI (PRC) dictionary file name')
    parser.add_argument('lsj_xml', help='Dictionary XML, gzipped')
    parser.add_argument('infl_xml', help='Morphology database, gzipped')
    args = parser.parse_args()

    with gzip.open(args.infl_xml, 'r') as f:
        inflections = get_inflections(f)
    with gzip.open(args.lsj_xml, 'r') as lsjfp, codecs.open(args.outfile, 'w', 'utf-8') as outfp:
        write_entries(lsjfp, outfp, inflections)

if __name__ == '__main__':
    main()
