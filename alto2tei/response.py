import collections
import os
import re
import sys

import requests
from lxml import etree

NS = {"s":"http://www.loc.gov/zing/srw/", "m":"info:lc/xmlns/marcxchange-v2"}

def unimarc(directory):
    cat_ark, manifest_title, manifest_date = manifest(directory)
    r = requests.get(f'http://catalogue.bnf.fr/api/SRU?version=1.2&operation=searchRetrieve&query=(bib.persistentid all "{cat_ark}")')
    root = etree.fromstring(r.content)
    if root.find('.//s:numberOfRecords', namespaces=NS).text=="0":
        r = requests.get(f'http://catalogue.bnf.fr/api/SRU?version=1.2&operation=searchRetrieve&query=(bib.title all "{manifest_title}")&maximumRecords=1')
        root = etree.fromstring(r.content)
    return root

def manifest(directory):
    r = requests.get(f"https://gallica.bnf.fr/iiif/ark:/12148/{os.path.basename(directory)}/manifest.json/")
    metadata = collections.deque(r.json()["metadata"])
    cat_ark = re.search(
        r"\/((?:ark:)\/\w+\/\w+)",
        [d for d in metadata if d["label"]=="Relation"][0]["value"])\
        .group(1)
    title = [d for d in metadata if d["label"]=="Title"][0]["value"]
    d = [d for d in metadata if d["label"]=="Date"][0]["value"]
    return cat_ark, title, d


if __name__ == "__main__":
    if len(sys.argv) > 1:
        directories = [path for path in sys.argv[1:] if os.path.isdir(path)]  # create a list of directories in data/*
        for directory in directories:
            root = unimarc(directory)
            with open(f'data/response_{os.path.basename(directory)}.xml', 'wb') as f:
                etree.ElementTree(root).write(f, encoding="utf-8", xml_declaration=True, pretty_print=True)