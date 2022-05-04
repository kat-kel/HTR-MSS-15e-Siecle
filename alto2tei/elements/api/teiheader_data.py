import collections
import os
import re

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
        perfect_match = False
        print("|        did not find perfect match from Gallica ark")
    else:
        perfect_match = True
        print("|        found perfect match from Gallica ark")
    manifest_data = {"manifest_title":manifest_title, "manifest_date":manifest_date}
    return root, perfect_match, manifest_data


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


def get_data(unimarc_xml):
    author_data = get_author(unimarc_xml)
    title_data = get_title(unimarc_xml)
    bib_data = get_bib(unimarc_xml, title_data)
    data = [author_data, title_data, bib_data]
    return data


def get_author(root):
    # if there is an author
    if root.find('.//m:datafield[@tag="700"]', namespaces=NS) is not None:
        authors = root.findall('.//m:datafield[@tag="700"]', namespaces=NS)
        author_data = []
        for i, author in enumerate(authors):
            if author.find('m:subfield[@code="o"]', namespaces=NS) is not None:
                author_id = author.find('m:subfield[@code="o"]', namespaces=NS).text
            else:
                author_id = None
            if author.find('m:subfield[@code="a"]', namespaces=NS) is not None:
                author_surname = author.find('m:subfield[@code="a"]', namespaces=NS).text
            else:
                author_surname = None
            if author.find('m:subfield[@code="b"]', namespaces=NS) is not None:
                author_forename = author.find('m:subfield[@code="b"]', namespaces=NS).text
            else:
                author_forename = None
            if author_surname:
                xmlid = {"{http://www.w3.org/XML/1998/namespace}id":f"{author_surname[:2]}{i}"}
            elif author_forename:
                xmlid = {"{http://www.w3.org/XML/1998/namespace}id":f"{author_forename[:2]}{i}"}
            else:
                xmlid = {"{http://www.w3.org/XML/1998/namespace}id":"None"}
            author_data.append({"author_id":author_id, "author_surname":author_surname, "author_forename":author_forename, "id":xmlid})
    else:
        author_data = None
    return author_data


def get_title(root):
    # try to get uniform title
    if root.find('.//m:datafield[@tag="500"]/m:subfield[@code="a"]', namespaces=NS) is not None:
        title_uniform = root.find('.//m:datafield[@tag="500"]/m:subfield[@code="a"]', namespaces=NS).text
    else:
        title_uniform = None

    # try to get form title
    if root.find('.//m:datafield[@tag="503"]/m:subfield[@code="a"]', namespaces=NS) is not None:
        title_form = root.findall('.//m:datafield[@tag="503"]/m:subfield[@code="a"]', namespaces=NS)[-1].text
    else:
        title_form = None
    title_data = {"title_uniform":title_uniform, "title_form":title_form}
    return title_data


def get_bib(root, title_data):
    # link to the work in the institution's catalogue
    if root.find('.//m:controlfield[@tag="003"]', namespaces=NS) is not None:
        ptr = root.find('.//m:controlfield[@tag="003"]', namespaces=NS).text
    else:
        ptr = None
    # publication place
    if root.find('.//m:datafield[@tag="210"]/m:subfield[@code="a"]', namespaces=NS) is not None:
        pubplace = root.find('.//m:datafield[@tag="210"]/m:subfield[@code="a"]', namespaces=NS).text
    elif root.find('.//m:datafield[@tag="620"]/m:subfield[@code="d"]', namespaces=NS) is not None:
        pubplace = root.find('.//m:datafield[@tag="620"]/m:subfield[@code="d"]', namespaces=NS).text
    else:
        pubplace = None
    # country code of publication place
    if root.find('.//m:datafield[@tag="102"]/m:subfield[@code="a"]', namespaces=NS) is not None:
        pubplace_att = root.find('.//m:datafield[@tag="102"]/m:subfield[@code="a"]', namespaces=NS).text
    else:
        pubplace_att = None
    # publisher
    if root.find('.//m:datafield[@tag="210"]/m:subfield[@code="c"]', namespaces=NS) is not None:
        publisher = root.find('.//m:datafield[@tag="210"]/m:subfield[@code="c"]', namespaces=NS).text
    else:
        publisher = None
    # date of publication
    if root.find('.//m:datafield[@tag="210"]/m:subfield[@code="d"]', namespaces=NS) is not None:
        d = root.find('.//m:datafield[@tag="210"]/m:subfield[@code="d"]', namespaces=NS).text
    else:
        d = None
    # country where the document is conserved
    if root.find('.//m:datafield[@tag="801"]/m:subfield[@code="a"]', namespaces=NS) is not None:
        country = root.find('.//m:datafield[@tag="801"]/m:subfield[@code="a"]', namespaces=NS).text
    else:
        country = None

    # city where the document is conserved
    settlement = "Paris"
    #if root.find('', namespaces=NS) is not None:  <-- needs work
        #settlement = root.find('', namespaces=NS).text

    # institution where the document is conserved
    repository = "BNF"
    #if root.find('', namespaces=NS) is not None:  <-- needs work
        #repository = root.find('', namespaces=NS).text

    # catalogue number of the document in the insitution
    if root.find('.//m:datafield[@tag="930"]/m:subfield[@code="a"]', namespaces=NS) is not None:
        idno = root.find('.//m:datafield[@tag="930"]/m:subfield[@code="a"]', namespaces=NS).text
    else:
        idno = None

    # type of document (manuscript or print)
    if root.find('.//m:datafield[@tag="200"]/m:subfield[@code="b"]', namespaces=NS) is not None:
        objectdesc = root.find('.//m:datafield[@tag="200"]/m:subfield[@code="b"]', namespaces=NS).text
    else:
        objectdesc = None
    data = {
            "ptr":ptr,
            "title":title_data["title_form"],
            "pubplace":pubplace,
            "pubplace_att":pubplace_att,
            "publisher":publisher,
            "date":d,
            "country":country,
            "settlement":settlement,
            "repository":repository,
            "idno":idno,
            "objectdesc":objectdesc
        }
    return data
