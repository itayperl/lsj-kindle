# coding:utf-8
# beta2unicode.py
#
# Version 2014-08-23 - fixes and refactoring by Itay Perl.  The new
# version uses the unicodedata module to find unicode codepoints instead of
# hardcoding them.
#
# James Tauber
# http://jtauber.com/
#
# You are free to redistribute this, but please inform me of any errors
#
# USAGE:
#
# trie = beta2unicodeTrie()
# beta = "LO/GOS\n";
# unicode, remainder = trie.convert(beta)
#
# - to get final sigma, string must end in \n
# - remainder will contain rest of beta if not all can be converted
import unicodedata
import itertools
import string
import re
import sys

class Trie:
    def __init__(self):
        self.root = [None, {}]

    def add(self, key, value):
        curr_node = self.root
        for ch in key:
            curr_node = curr_node[1].setdefault(ch, [None, {}])
        curr_node[0] = value

    def find(self, key):
        curr_node = self.root
        for ch in key:
            try:
                curr_node = curr_node[1][ch]
            except KeyError:
                return None
        return curr_node[0]

    def findp(self, key):
        curr_node = self.root
        remainder = key
        for ch in key:
            try:
                curr_node = curr_node[1][ch]
            except KeyError:
                return (curr_node[0], remainder)
            remainder = remainder[1:]
        return (curr_node[0], remainder)

    def convert(self, keystring):
        valuestring = ""
        key = keystring
        while key:
            value, key = self.findp(key)
            if not value:
                return (valuestring, key)
            valuestring += value
        return (valuestring, key)

def beta2unicodeTrie():
    t = Trie()
    LETTERS = {
        "A": "Alpha",
        "B": "Beta",
        "G": "Gamma",
        "D": "Delta",
        "E": "Epsilon",
        "V": "Digamma",
        "Z": "Zeta",
        "H": "Eta",
        "Q": "Theta",
        "I": "Iota",
        "K": "Kappa",
        "L": "Lamda",
        "M": "Mu",
        "N": "Nu",
        "C": "Xi",
        "O": "Omicron",
        "P": "Pi",
        "R": "Rho",
        "S": "Sigma",
        "S1": "Sigma",
        "S2": "Final Sigma",
        "J": "Final Sigma",
        "S3": "Lunate Sigma",
        "T": "Tau",
        "U": "Upsilon",
        "F": "Phi",
        "X": "Chi",
        "Y": "Psi",
        "W": "Omega",
    }
    _DIACRITICS = {
        '(': 'DASIA',
        ')': 'PSILI',
        '/': 'OXIA',
        '\\': 'VARIA',
        '=': 'PERISPOMENI',
        '|': ('YPOGEGRAMMENI', 'PROSGEGRAMMENI'),
        '+': 'DIALYTIKA',
        '&': 'MACRON'
    }
    DIACRITICS = { i: (j if type(j) is tuple else (j, j)) for i,j in _DIACRITICS.iteritems() }

    def add(beta):
        # characters with an irregular name
        IRREGULAR = {
            'GREEK CAPITAL LETTER DIGAMMA': 'GREEK LETTER DIGAMMA',
            'GREEK SMALL LETTER LUNATE SIGMA': 'GREEK LUNATE SIGMA SYMBOL',
            'GREEK CAPITAL LETTER LUNATE SIGMA': 'GREEK CAPITAL LUNATE SIGMA SYMBOL',
        }

        is_capital = '*' in beta
        low_beta = beta.replace('*', '')

        letter = re.search('|'.join(re.escape(x) for x in sorted(LETTERS, key=lambda l: -len(l)) ), low_beta).group(0)
        diacs = [ DIACRITICS[x][is_capital] for x in low_beta.replace(letter, '') ]
        # the only precedence difference between unicode names and betacode
        if 'DIALYTIKA' in diacs:
            diacs.remove('DIALYTIKA')
            diacs.insert(0, 'DIALYTIKA')

        name = 'GREEK {} LETTER {}'.format({ True: 'CAPITAL', False: 'SMALL' }[is_capital], LETTERS[letter].upper() )
        if diacs:
            name += ' WITH ' + ' AND '.join(diacs)

        name = IRREGULAR.get(name, name)
        try:
            found = unicodedata.lookup(name)
        except KeyError:
            raise KeyError(u'Not found {} (name: {})'.format(beta, name))

        t.add(beta, found)

    def _uniq(seq):
        seen = set()
        seen_add = seen.add
        return [ x for x in seq if not (x in seen or seen_add(x))]

    # add both lowercase and uppercase versions of a word
    def add2(n):
        # known missing characters
        SKIP_UPPER = [
            'S2', 'J', # capital final sigmal, obviously
            'U)', 'U)/', 'U)\\', 'U)=',
            'R)',
        ]
        assert n[0] in LETTERS
        add(n)

        if n in SKIP_UPPER:
            return

        versions = _uniq([
            '*'+ n,
            # swap diacs and letter (iota subscript remains at the end)
            re.sub(r'([A-Z]\d?)([^|]*)', r'*\2\1', n),
            # swap diacs and letter, asterisk inbetween
            re.sub(r'([A-Z]\d?)([^|]*)', r'\2*\1', n),
        ])
        for ver in versions:
            add(ver)

    for l in LETTERS:
        add2(l)

    # Final sigma
    t.add("S\n",    u"\u03C2")
    t.add("S,",     u"\u03C2,")
    t.add("S.",     u"\u03C2.")
    t.add("S:",     u"\u03C2:")
    t.add("S;",     u"\u03C2;")
    t.add("S]",     u"\u03C2]")
    t.add("S@",     u"\u03C2@")
    t.add("S_",     u"\u03C2_")

    add("I+")
    add("U+")

    for l in 'AEHIOUW':
        grp1 = ('', ')', '(')
        grp2 = ('', '/', '\\')
        # add all combinations
        for d in (''.join(x) for x in itertools.product(grp1, grp2)):
            if d:
                add2(l + d)

    for l in 'AHIUW':
        add2(l + ")=")
        add2(l + "(=")

    add2("A)/|")
    add2("A(/|")
    add2("A(|")
    add2("A)|")
    add2("A(=|")
    add2("A)=|")
    add2("H)|")
    add2("H(|")
    add2("H)/|")
    add2("H)=|")
    add2("H(=|")
    add2("W)|")
    add2("W(=|")
    add2("W)=|")
    add2("W)/|")
    add2("W)\\|")

    add("A=")
    add("H=")
    add("I=")
    add("U=")
    add("W=")

    add("I\\+")
    add("I/+")
    add("I+/")
    add("U\\+")
    add("U/+")

    add("A|")
    add("A/|")
    add("A\\|")
    add("H|")
    add("H/|")
    add("H\\|")
    add("W|")
    add("W/|")
    add("W\\|")

    add("A=|")
    add("H=|")
    add("W=|")

    add2("R(")
    add2("R)")

    # Additions due to LSJ
    t.add('*)R', unicodedata.lookup('GREEK PSILI') + unicodedata.lookup('GREEK CAPITAL LETTER RHO'))
    add('A)=|')
    add('A)|')
    add('H(/|')

    # non-letters
    #
    t.add("/",      u"\u2019")
    t.add("-",      u"-")
    t.add(u"\u2014", u"\u2014")
    t.add("^", u"^")
    
#    t.add("(null)", u"(null)")
#    t.add("&", "&")
    
    t.add("0", u"0")
    t.add("1", u"1")
    t.add("2", u"2")
    t.add("3", u"3")
    t.add("4", u"4")
    t.add("5", u"5")
    t.add("6", u"6")
    t.add("7", u"7")
    t.add("8", u"8")
    t.add("9", u"9")
    
    t.add("@", u"@")
    t.add("$", u"$")
    
    t.add(" ", u" ")
    
    t.add(".", u".")
    t.add(",", u",")
    t.add('"', u'"')
    t.add("'", u"'")
    t.add(":", u":")
    t.add(";", u";")
    t.add("!", u"!")
    t.add("_", u"_")
    t.add("#", u"#")

    t.add("[", u"[")
    t.add("]", u"]")
    
    t.add("\n", u"")
    
    
    return t

trie = beta2unicodeTrie()

def beta2unicode(word):
    # remove final asterisk, not sure what it means
    w = word.rstrip('*')
    # swap /(, =) etc.
    w = re.sub(r'([/\\=])([()])', r'\2\1', w)
    # swap +/, +\
    w = re.sub(r'\+([/\\])', r'\1+', w)
    word = w
    u, r = trie.convert(word.upper() + '\n')
    if r.strip(string.whitespace + '?'):
        return None
    
    return u + r

__all__ = [ 'beta2unicode' ]
