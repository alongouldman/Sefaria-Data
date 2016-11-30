# encoding=utf-8

import codecs
import re
from data_utilities.util import ja_to_xml
from sources.functions import post_text, post_index
from sefaria.model import *

#

def ari_parse():
    with codecs.open('yitzira_mishna.txt', 'r', 'utf-8') as fp:
        lines = fp.readlines()
    parsed = []
    perek = []
    mishna = []
    starting = None
    # check if we got to the end of the legend and change to started
    for line_num, line in enumerate(lines):
        if line == u'\n':
            starting = line_num + 1
            break

    for line in lines[starting:]:
        if line.find(u'@00') == 0:
            if perek:
                mishna = ' '.join(mishna)
                perek.append(mishna)
                mishna = []
                parsed.append(perek)
                perek = []
        elif line.find(u'@22') == 0:
            if mishna:
                mishna = ''.join(mishna)
                perek.append(mishna)
                mishna = []
        else:
            small = re.sub(u'@(44)', u'<small>', line)
            end_small = re.sub(u'@(45)', u'</small>', small)
            fixed_line = re.sub(u'@(11|12|66|67)', u'', end_small)
            mishna.append(fixed_line.strip())

    mishna = ' '.join(mishna)
    perek.append(mishna)
    parsed.append(perek)
    ja_to_xml(parsed,['perek', 'mishna'])
    return parsed

ari_parse()

def post_this():
    text_version = {
        'versionTitle': 'Sefer Yetzirah, Warsaw 1884',
        'versionSource': 'http://primo.nli.org.il/primo_library/libweb/action/dlDisplay.do?vid=NLI&docId=NNL_ALEPH001310968',
        'language': 'he',
        'text': ari_parse()
    }

    schema = JaggedArrayNode()
    schema.add_title('Sefer Yetzirah Ari Version', 'en', True)
    schema.add_title(u'ספר יצירה גרסאת הארי', 'he', True)
    schema.key = 'Sefer Yetzirah Ari Version'
    schema.depth = 2
    schema.addressTypes = ['Integer', 'Integer']
    schema.sectionNames = ['Chapter', 'Mishnah']
    schema.validate()

    index_dict = {
        'title': 'Sefer Yetzirah Ari Version',
        'categories': ['Kabbalah'],
        'schema': schema.serialize() # This line converts the schema into json
    }
    post_index(index_dict)

    post_text('Sefer Yetzirah Ari Version', text_version, index_count='on')

post_this()