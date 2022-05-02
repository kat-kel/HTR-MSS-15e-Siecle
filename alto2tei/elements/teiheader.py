import json
import os
import urllib.request
import re

from lxml import etree
from SPARQLWrapper import JSON, SPARQLWrapper


def teiheader(directory, root):
    sparql = sparql_data(directory)
    manifest = manifest_data(directory)
    teiheader = etree.SubElement(root, "teiHeader")
    filedesc = etree.SubElement(teiheader, "fileDesc")
    filedesc = make_titlestmt(filedesc, sparql, manifest)
    #filedesc = make_souredesc(filedesc, sparql, manifest)
    return root

def make_titlestmt(filedesc, sparql, manifest):
    
    titlestmt = etree.SubElement(filedesc, "titleStmt")
    title_titlestmt = etree.SubElement(titlestmt, "title")
    title_titlestmt.text = manifest["title"]

    titlestmt = author_titlstmt(titlestmt, sparql, manifest)
    titlestmt = resp_stmt(titlestmt)

    return filedesc


def author_titlstmt(titlestmt, sparql, manifest):
    if manifest["creator"]:
        try:
            author = re.search(r"(.+)\s[\(|\.]", manifest["creator"]).group(1)
            author_titlestmt = etree.SubElement(titlestmt, "author")
            author_titlestmt.attrib["{http://www.w3.org/XML/1998/namespace}id"] = author[:3]
            persname = etree.SubElement(author_titlestmt, "persName")
            author_name = etree.SubElement(persname, "name")
            author_name.text = author
            author_persname_ptr = etree.SubElement(persname, "ptr")
            author_persname_ptr.attrib["type"] = "isni"
            author_persname_ptr.attrib["target"] = sparql["author_isni"]
        except:
            print("did not add author")
    else:
        pass
    return titlestmt


def resp_stmt(titlestmt):
    editor1_forename = "Kelly"
    editor1_surname = "Christensen"
    editor1_orcid = "000000027236874X"
    respstmt = etree.SubElement(titlestmt, "respStmt")
    respstmt.attrib["{http://www.w3.org/XML/1998/namespace}id"] = editor1_forename[0]+editor1_surname[0]
    resp = etree.SubElement(respstmt, "resp")
    resp.text = "restructured by"
    editor_respstmt_persname = etree.SubElement(respstmt, "persName")
    editor_respstmt_forename = etree.SubElement(editor_respstmt_persname, "forename")
    editor_respstmt_forename.text = editor1_forename
    editor_respstmt_surname = etree.SubElement(editor_respstmt_persname, "surname")
    editor_respstmt_surname.text = editor1_surname
    editor_respstmt_ptr = etree.SubElement(editor_respstmt_persname, "ptr")
    editor_respstmt_ptr.attrib["type"] = "orcid"
    editor_respstmt_ptr.attrib["target"] = editor1_orcid


def make_souredesc(filedesc, sparql, manifest):
    sourcedesc = etree.SubElement(filedesc, "publicationStmt")
    bibl = etree.SubElement(sourcedesc, "bibl")
    #author_bibl = etree.SubElement(bibl, "author")
    #author_bibl.text = m["creator"][0]
    #if author_isni is not None:
        #author_bibl.attrib["xml_id"] = author_isni["value"]
    if sparql["publisher"] is not None:
        publisher_bibl = etree.SubElement(bibl, "publisher")
        publisher_bibl.text = sparql["publisher"]["value"]
    date_bibl = etree.SubElement(bibl, "date")
    date_bibl.attrib["when"] = manifest["date"]
    date_bibl.text = manifest["date"]
    return filedesc


def manifest_data(directory):
    r = urllib.request.urlopen(f"https://gallica.bnf.fr/iiif/ark:/12148/{os.path.basename(directory)}/manifest.json/")
    data = json.loads(r.read())
    title = data["metadata"][5]["value"]
    creator = data["metadata"][9]["value"]
    date = data["metadata"][6]["value"]
    manifest = {"title":title, "creator":creator, "date":date}
    return manifest


def sparql_data(directory):
    sparql = SPARQLWrapper("http://data.bnf.fr/sparql")
    # the request
    sparql.setQuery("""PREFIX foaf: <http://xmlns.com/foaf/0.1/>
                       PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
                       PREFIX dcterms: <http://purl.org/dc/terms/>
                       PREFIX rdam: <http://rdaregistry.info/Elements/m/>
                       PREFIX owl: <http://www.w3.org/2002/07/owl#>
                       PREFIX rdarelationships: <http://rdvocab.info/RDARelationshipsWEMI/>
                       PREFIX rdagroup1elements: <http://rdvocab.info/Elements/>
                       PREFIX marcrel: <http://id.loc.gov/vocabulary/relators/>
                       PREFIX isni: <http://isni.org/ontology#>
                       SELECT ?title ?author ?name_author ?publication_place ?publisher_name 
                       ?publication_date ?isniAuthor ?sameas
                       WHERE {
                       ?manifestation <http://rdvocab.info/RDARelationshipsWEMI/electronicReproduction> <https://gallica.bnf.fr/ark:/12148/""" + os.path.basename(directory) + """>.
                       ?manifestation dcterms:title ?title;
                       <http://rdvocab.info/RDARelationshipsWEMI/expressionManifested> ?expression.
                       OPTIONAL {?manifestation rdagroup1elements:publishersName ?publisher_name}.
                       OPTIONAL {?manifestation rdagroup1elements:placeOfPublication ?publication_place}.
                       ?manifestation dcterms:date ?publication_date.
                       OPTIONAL {?expression marcrel:aut ?author.
                       ?authorConcept foaf:focus ?author.
                       ?authorConcept owl:sameAs ?sameas FILTER(contains(str(?sameas), 'biblissima')).
                       ?authorConcept isni:identifierValid ?isniAuthor.
                       ?authorConcept skos:prefLabel ?name_author}.
                       }"""
                    )

    sparql.setReturnFormat(JSON)
    r = sparql.query().convert()

    try:
        pub_place = r["results"]["bindings"][0].get("publication_place")["value"]
    except:
        pub_place = "none"
    try:
        publisher = r["results"]["bindings"][0].get("publisher_name")["value"]
    except:
        publisher = "none"
    try:
        author_isni = r["results"]["bindings"][0].get("isniAuthor")["value"]
    except:
        author_isni = "none"

    sparql = {"publisher":publisher, "pub_place":pub_place, "author_isni":author_isni}

    return sparql
