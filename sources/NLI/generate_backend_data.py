# encoding=utf-8

import re
import os
import json
import codecs
from sources.NLI.database import Database
from bs4 import BeautifulSoup

import django
django.setup()
from sefaria.model import *


def generate_qa_document(data_list, outfile='image_qa.html'):
    # todo: add sefaria text for each ref
    soup = BeautifulSoup('', 'html5lib')
    style = soup.new_tag('style')
    style.string = '''
    table,
    td {
        border: 1px solid #333;
    }

    thead {
        background-color: #333;
        color: #fff;
    }
    '''
    soup.head.append(style)

    table = soup.new_tag('table')
    soup.body.append(table)
    thead, tbody = soup.new_tag('thead'), soup.new_tag('tbody')
    table.append(thead)
    table.append(tbody)

    head_row = soup.new_tag('tr')
    thead.append(head_row)
    for header in ["Image_Content", "Expanded_Refs", "image_thumbnail", "image_url"]:
        header_obj = soup.new_tag('th')
        header_obj.string = header
        head_row.append(header_obj)

    for data_obj in data_list:
        table_row = soup.new_tag('tr')
        tbody.append(table_row)
        columns = [soup.new_tag('td') for _ in range(4)]

        columns[0].string = data_obj['image_content']

        ref_table = soup.new_tag('table')

        if len(data_obj['expanded_refs']) > 10:
            expanded_refs = data_obj['expanded_refs'][:5] + data_obj['expanded_refs'][-5:]  # remove clutter
        else:
            expanded_refs = data_obj['expanded_refs']

        for tref in expanded_refs:  # 1 indexed so we know which number item we see
            ref_row = soup.new_tag('tr')
            ref_table.append(ref_row)
            tref_cell, tref_text_cell = soup.new_tag('td'), soup.new_tag('td')
            oref = Ref(tref)

            sefaria_link = soup.new_tag('a')
            sefaria_link['href'] = 'https://www.sefaria.org/{}'.format(oref.url())
            sefaria_link['target'] = '_blank'
            sefaria_link.string = tref
            tref_cell.append(sefaria_link)

            ref_row.append(tref_cell)
            tref_text_cell.string = oref.text('he').text
            ref_row.append(tref_text_cell)
        columns[1].append(ref_table)

        thumbnail = soup.new_tag('img')
        thumbnail['src'] = re.sub(r'\.jpg', '_thumbnail.jpg', data_obj['image_url'])
        columns[2].append(thumbnail)

        image_url = soup.new_tag('a')
        image_url['href'] = data_obj['image_url']
        image_url['target'] = "_blank"
        image_url.string = 'full image'
        columns[3].append(image_url)
        for column in columns:
            table_row.append(column)

    with codecs.open(outfile, 'w', 'utf-8') as fp:
        fp.write(str(soup))


def expand_refs_from_image_title(image_title, ref_enhancement=None):
    # assuming all titles can be split by - and have no skips (;) (appears true for 1723)

    if re.search(r';\s+', image_title):
        title_sections = re.split(r';\s+', image_title)
        expansions = []
        for section in title_sections:
            expansions.extend(expand_refs_from_image_title(section, ref_enhancement))
        return expansions

    def enhance_ref(tref): return '{} {}'.format(ref_enhancement, tref)

    tr1, tr2 = re.split(r'\s*-\s*', image_title)
    if ref_enhancement:
        tr1, tr2 = enhance_ref(tr1), enhance_ref(tr2)
    if not Ref.is_ref(tr1) or not Ref.is_ref(tr2):
        return None
    or1, or2 = Ref(tr1), Ref(tr2)
    if or1.book != or2.book:  # image contains the boundary between two tractates
        starting_refs, ending_refs = [], []

        while or1 is not None:
            starting_refs.append(or1)
            or1 = or1.next_segment_ref()

        while or2 is not None:
            ending_refs.append(or2)
            or2 = or2.prev_segment_ref()

        ref_list = starting_refs + ending_refs[::-1]
    else:
        ref_list = or1.to(or2).all_segment_refs()

    return [r.normal() for r in ref_list]


def leningrad_segments(tref):
    ref_portions = re.split(r'\s*;\s*', tref)

    if any(not Ref.is_ref(portion) for portion in ref_portions):
        print("could not resolve {}".format(tref))
        return []

    segments = []
    for portion in ref_portions:
        segments.extend([r.normal() for r in Ref(portion).all_segment_refs()])

    return segments


def start_end_refs(book_category):
    all_books = library.get_indexes_in_category(book_category)
    se_refs = set()
    for book in all_books:
        oref = Ref(book)
        se_refs.add(oref.last_segment_ref().normal())
        se_refs.add((oref.first_available_section_ref().all_segment_refs()[0].normal()))

    return se_refs


def category_ref_sort_key(category_list):
    book_list = []
    for book_category in category_list:
        book_list.extend(library.get_indexes_in_category(book_category))

    tractate_order = {tractate: tractate_num for tractate_num, tractate in
                      enumerate(book_list)}

    def key_method(tref):
        oref = Ref(tref)
        return tractate_order[oref.book], oref.sections
    return key_method


if __name__ == '__main__':
    filenames = sorted([f_name for f_name in os.listdir('./kaufman')
                        if not re.search(r'thumbnail\.jpg$', f_name)])

    db = Database()
    db.cursor.execute('Select * FROM TblImages WHERE Im_Ms=1723 AND Im_Title IS NOT NULL')
    images = [f['Im_Title'] for f in db.cursor.fetchall()]

    filenames = filenames[2:]
    filenames = filenames[:-1]
    filenames.pop(251)
    filenames.pop(251)
    # print (images[0])
    print(len(filenames) - len(images))
    print(len(images))

    image_data_list = [{
        'image_content': '{} / {} / {}'.format(f_name, im_title, image_num),
        'expanded_refs': expand_refs_from_image_title(im_title, ref_enhancement='משנה'),
        'image_url': 'https://storage.googleapis.com/sefaria-manuscripts/kaufman_a_50/{}'.format(f_name)
    } for image_num, (f_name, im_title) in enumerate(zip(filenames, images))]
    # qa_images = image_data_list[::50]
    # qa_images.append(image_data_list[-1])

    # we have off-by-one errors in Munich. For now, add every 50-th image to qa and try and identify skips
    qa_images = []
    munich_image_data_list = []
    with open('./munich_images/munich_filemap.json') as fp:
        munich_filemap = json.load(fp)

    munich_images = [f for f in os.listdir('./munich_images') if re.search(r'(?<!thumbnail)\.jpg$', f)]
    ref_expansion = {}
    for munich_file in munich_filemap:
        assert munich_file['image_file'] not in ref_expansion
        ref_expansion[munich_file['image_file']] = munich_file['expaned_refs']

    for munich_image in munich_images:
        full_file_path = os.path.join('munich_images', munich_image)

        image_data = {
            'image_content': munich_image,
            'expanded_refs': ref_expansion.get(full_file_path, []),
            'image_url': 'https://storage.googleapis.com/sefaria-manuscripts/munich-manuscript/{}'.format(munich_image)

        }
        if os.path.join('munich_images', munich_image) in ref_expansion:
            munich_image_data_list.append(image_data)

        else:
            qa_images.append(image_data)

    sort_key = category_ref_sort_key(["Bavli", "Mishnah"])
    munich_image_data_list.sort(key=lambda x: sort_key(x['expanded_refs'][0]))

    talmud_start_end_refs = start_end_refs("Bavli")

    for image_data in munich_image_data_list:
        if any(extended in talmud_start_end_refs for extended in image_data['expanded_refs']):
            qa_images.append(image_data)

    with open('Leningrad_map.json') as fp:
        leningrad_map = json.load(fp)

    leningrad_image_data_list = [
        {
            'image_content': l_value,
            'expanded_refs': leningrad_segments(l_value),
            'image_url': 'https://storage.googleapis.com/sefaria-manuscripts/Leningrad/{}'.format(l_key)
        }
        for l_key, l_value in leningrad_map.items()
    ]

    sort_key = category_ref_sort_key(["Tanakh"])
    leningrad_image_data_list.sort(key=lambda x:sort_key(x['expanded_refs'][0]))


    tanakh_start_end_refs = start_end_refs("Tanakh")
    for image_data in leningrad_image_data_list:
        if any(extended in tanakh_start_end_refs for extended in image_data['expanded_refs']):
            qa_images.append(image_data)

    generate_qa_document(qa_images)
    image_data_list.extend(munich_image_data_list)
    image_data_list.extend(leningrad_image_data_list)
