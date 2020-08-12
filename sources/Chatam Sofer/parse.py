import django
django.setup()
import csv
from sources.functions import *
import os
import re
import time
from data_utilities.dibur_hamatchil_matcher import *
def parse_daf(text, daf, prev_daf, amud, line):
    amud = getGematria(amud)
    if amud not in [1, 2, 71, 72]:
        amud = 1 if "'" in daf else 2
    amud = amud % 2
    curr_daf = getGematria(daf) * 2 - (amud)
    curr_daf = fix_daf(daf, curr_daf, prev_daf, amud)
    prev_daf = curr_daf
    text[curr_daf] = []
    return curr_daf, prev_daf

def fix_daf(text, daf, prev, amud):
    if daf > prev + 1 and text.startswith("ד") and len(text) in [3, 4]:
        return (getGematria(text[1:]) * 2) - amud
    elif daf > prev + 1:
        text = text.replace("(", "").replace(")", "")
        return (getGematria(text[0]) * 2) - amud
    elif daf < prev:
        return None
    else:
        return daf

def process_old_files():
    for f in os.listdir("."):
        text = {}
        if f.endswith("txt"):
            title = u" ".join(f.split(".txt")[:-1])
            prev_daf = 3
            text[prev_daf] = []
            with open(f) as file:
                lines = list(file)

                for n, line in enumerate(lines):
                    poss_daf = re.search("[@\d(]{3,4}דף \S{1,} \S{1,} ", line)
                    poss_daf_2 = re.search("@\d+(\(.*?\)) ", line)
                    if poss_daf:
                        print(" ".join(line.split()[:5]))
                        marker, daf, amud = poss_daf.group(0).split()
                        curr_daf, prev_daf = parse_daf(text, daf, prev_daf, amud, line)
                        line = line.replace(poss_daf.group(0), "")
                    elif poss_daf_2:
                        print(" ".join(line.split()[:5]))
                        info = poss_daf_2.group(1).split()
                        if len(info) == 1:
                            daf = prev_daf
                            amud = info[0]
                            if amud == '(ע"ב)':
                                daf = prev_daf if prev_daf % 2 == 0 else prev_daf + 1
                        elif len(info) == 2:
                            daf = info[0]
                            amud = info[1]
                        elif len(info) == 3:
                            daf = info[1]
                            amud = info[2]

                        amud = getGematria(amud)
                        if daf == '(שם':
                            daf = prev_daf if prev_daf % 2 == 0 else prev_daf + 1
                        elif len(info) > 1:
                            poss_daf = getGematria(daf) * 2
                            # if poss_daf > prev_daf + 5:
                            #     poss_daf = getGematria(daf[1]) * 2
                            amud = amud % 2
                            poss_daf = poss_daf - amud
                            daf = fix_daf(daf, poss_daf, prev_daf, amud)
                        prev_daf = daf
                        line = line.replace(poss_daf_2.group(0), "")
                        if prev_daf not in text:
                            text[prev_daf] = []
                    text[prev_daf].append(line)

def create_index(en_title, title):
    he_title = "חידושי חתם סופר"
    if en_title in ["Ketubot", "Chullin"]:
        root = SchemaNode()
        root.add_primary_titles("Chidushei Chatam Sofer on {}".format(en_title), u"{} על {}".format(he_title, title))
        default = JaggedArrayNode()
        default.default = True
        default.key = "default"
        default.add_structure(["Daf", "Paragraph"], address_types=["Talmud", "Integer"])
        root.append(default)
        mahadura = JaggedArrayNode()
        mahadura.add_structure(["Daf", "Paragraph"], address_types=["Talmud", "Integer"])
        mahadura.add_primary_titles("Mahadurah Tanina", "מהדורא תנינא")
        root.append(mahadura)
        root.validate()
    else:
        root = JaggedArrayNode()
        root.add_structure(["Daf", "Paragraph"], address_types=["Talmud", "Integer"])
        root.add_primary_titles("Chidushei Chatam Sofer on {}".format(en_title), u"{} על {}".format(he_title, title))
        root.validate()
    indx = {
        "schema": root.serialize(),
        "title": "Chidushei Chatam Sofer on {}".format(en_title),
        "categories": ["Talmud", "Bavli", "Commentary", "Chidushei Chatam Sofer"],
        "dependence": "Commentary",
        "base_text_titles": [en_title],
        "collective_title": "Chidushei Chatam Sofer"
    }
    post_index(indx)

if __name__ == "__main__":
    i = get_index_api("Esther Rabbah")
    links = []
    files = os.listdir(".")
    links_per_masechtot = {}
    links_per_daf = {}
    comments_per_masechtot = {}
    for f in files:
        if not f.endswith("tsv"):
            continue
        title = f.split(".")[0].split(" - ")[-1]
        try:
            en_title = library.get_index(title).title
        except:
            en_title = title
        text = {}
        links_per_masechtot[en_title] = 0
        links_per_daf[en_title] = {}
        comments_per_masechtot[en_title] = 0
        dhs = {}
        daf_as_num = 0
        prev_daf_as_num = 0
        with open(f) as tsv_file:
            for line in tsv_file:
                daf, comment = line.split("\t", 1)
                if daf:
                    daf_as_num = getGematria(daf) * 2
                    amud = 1 if "." in daf else 0
                    daf_as_num -= amud
                    assert daf_as_num > prev_daf_as_num
                else:
                    daf_as_num = prev_daf_as_num

                dh = comment.split(".")[0]
                if dh.count(" ") > 10:
                    dh = ""
                if daf_as_num not in text:
                    text[daf_as_num] = []
                    dhs[daf_as_num] = []

                if "@99" in comment:
                    comment = "<b>"+removeAllTags(comment)+"</b>"
                    text[daf_as_num].append(comment)
                elif "@11" in comment:
                    comment = removeAllTags(comment)
                    dhs[daf_as_num].append(removeAllTags(dh))
                    text[daf_as_num].append(comment)

                prev_daf_as_num = daf_as_num
            for daf, comments in dhs.items():
                daf = AddressTalmud.toStr("en", daf)
                comm_ref = "Chidushei Chatam Sofer on {} {}".format(en_title, daf)
                base_ref = "{} {}".format(en_title, daf) if "Mahadura" not in en_title else "{} {}".format(en_title.split(",")[0], daf)
                new_links = match_ref_interface(base_ref, comm_ref, comments, lambda x: x.split(), lambda x: x)
                links += new_links
                links_per_masechtot[en_title] += len(new_links)
                links_per_daf[en_title][comm_ref] = "{}/{}".format(len(new_links), len(comments))
                comments_per_masechtot[en_title] += len(comments)
            text = convertDictToArray(text)
            send_text = {
                "versionSource": "https://www.nli.org.il/he/books/NNL_ALEPH002036613/NLI",
                "versionTitle": "Chidushei Chatam Sofer, 1864-1908",
                "text": text,
                "language": "he"
            }
            # if "Mahadura" not in en_title:
            #     create_index(en_title, title)
            #post_text("Chidushei Chatam Sofer on {}".format(en_title), send_text, index_count="on")

    # print("Len links is {}".format(len(links)))
    # for i in range(2000, 2274, 200):
    #     print("Posting {} through {}".format(i, 200+i))
    #     post_link(links[i:200+i])
    #     time.sleep(2)
    with open("links_per_masechta.csv", 'w') as f:
        masechta_writer = csv.writer(f)
        masechta_writer.writerow(["Masechet",  "Links", "Total segments"])
        sort_key = lambda x: AddressTalmud(1).toNumber("en", x.split()[-1])

        for en_title in links_per_masechtot:
            print(en_title)
            masechta_writer.writerow([en_title, links_per_masechtot[en_title], comments_per_masechtot[en_title]])
            with open("links_per_daf_in_{}.csv".format(en_title), 'w') as f:
                writer = csv.writer(f)
                for daf in sorted(links_per_daf[en_title].keys(), key=sort_key):
                    writer.writerow([daf.split()[-1], links_per_daf[en_title][daf]])