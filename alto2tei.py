import os
import sys
from lxml import etree
import re
from collections import defaultdict

NS = {'a':"http://www.loc.gov/standards/alto/ns-v4#"}  # namespace for the Alto xml


def order_files(dir):
    """Generates a numerically ordered list of file names from the given directory path.
        This resolves any issue with file names ordered in the directory alphabetically.
        For example, it corrects ["file_f10", "file_f9"] to ["file_f9", "file_f10"].

    Returns:
        ordered_files (list): file names from directory ordered by folio number
    """
    # parses file names from a directory (given as an argument in command line) into a list of strings
    file_names = [file for file in os.listdir(dir) if file.endswith(".xml")]
    # extracts the folio number into a list, and orders the list of integers
    folio_numbers = sorted([int(re.search(r"(.*f)(\d+)", file).group(2)) for file in file_names])
    # parses the folio number's prefix: eg. "f" or "document_f"
    prefix = re.search(r"(.*f)(\d+)", file_names[0]).group(1)
    # constructs an ordered list of the complete file names by concatenating the prefix and folio number into a list of strings
    ordered_files = [prefix+str(number)+".xml" for number in folio_numbers]
    return ordered_files


def tags(ordered_files, dir):
    root = etree.parse(f"{dir}/{ordered_files[0]}").getroot()
    tags = [t.attrib for t in root.findall('.//a:OtherTag', namespaces=NS)]
    collect = defaultdict(dict)
    for d in tags:
        collect[d["ID"]] = d["LABEL"]
    tags_dict = dict(collect)
    return tags_dict


def page_attributes(root, dir, folio):
    """Generates a dictionary of attributes for the TEI <surface> element which adapts the <Page> element
        of the ALTO file passed as an argument.

    Args:
        file (string): name of an ALTO file
        dir (string): name of the directory containing the ALTO file

    Returns:
        page_attributes (dictionary): attributes for TEI file's <surface>
    """    
    # get attributes of <Page>
    att_list = root.find('.//a:Page', namespaces=NS).attrib
    # create a dictionary of attributes for the TEI adaptation of this ALTO file's <Page>
    page_attributes = {
        "{http://www.w3.org/XML/1998/namespace}id":f"{os.path.basename(dir)}_f{folio}",
        "n":att_list["PHYSICAL_IMG_NR"],
        "ulx":"0",
        "uly":"0",
        "lrx":att_list["WIDTH"],
        "lry":att_list["HEIGHT"]
    }
    return page_attributes


def zone_attributes(root, dir, tags, folio, parent, zone):
    zones = root.findall(f'.//a:{parent}a:{zone}', namespaces=NS)
    att_list = [z.attrib for z in zones]
    points = [z.find('.//a:Polygon', namespaces=NS).attrib for z in zones]
    block_attributes = []
    parent_list = []
    for i in range(len(zones)):
        tag_parts = re.match(r"(\w+):?(\w+)?#?(\d?)?", str(tags[att_list[i]["TAGREFS"]]))
        # the 3 groups of this regex parse the following expected tag syntax: MainZone:column#1 --> (MainZone)(column)(1)
        type = tag_parts.group(1)
        subtype = tag_parts.group(2) or "none"
        n = tag_parts.group(3) or "none"
        sep = " "
        zone_points = sep.join([re.sub(r"\s", ",", x) for x in re.findall(r"(\d+ \d+)", points[i]["POINTS"])])
        x = att_list[i]["HPOS"]
        y = att_list[i]["VPOS"]
        w = att_list[i]["WIDTH"]
        h = att_list[i]["HEIGHT"]
        zone_att = {
            "{http://www.w3.org/XML/1998/namespace}id":f"f{folio}_z{i+1}",
            "type":type,
            "subtype":subtype,
            "n":n,
            "points":zone_points,
            "source":f"https://gallica.bnf.fr/iiif/ark:/12148/{os.path.basename(dir)}/f{folio}/{x},{y},{w},{h}/full/0/native.jpg"
        }
        block_attributes.append(zone_att)
        parent_list.append(att_list[i]["ID"])
    return block_attributes, parent_list



def make_tei(ordered_files, dir):
    """Constructs a TEI file for the whole document, passes in each page's information (taken from ALTO files), 
        and outputs one XML-TEI file.

    Args:
        ordered_files (list): list of ALTO file names in the directory ordered by folio number
        dir (string): name of the directory containing the ALTO files
    """    
    # get dictionary of tags from this document
    tag_dict = tags(ordered_files, dir)

    # make the root <alto> and assign its attributes
    tei_root_att = {"xmlns":"http://www.tei-c.org/ns/1.0", "{http://www.w3.org/XML/1998/namespace}id":f"ark_12148_{os.path.basename(dir)}"}
    tei_root = etree.Element("TEI", tei_root_att)

    # create <sourceDoc> and its child <surfaceGrp>
    sourceDoc = etree.SubElement(tei_root, "sourceDoc")
    surfaceGrp = etree.SubElement(sourceDoc, "surfaceGrp")

    # for every page in the document, create a <surface> and assign it attributes taken from the ALTO file
    for file in ordered_files:
        folio = re.search(r"(.*f)(\d+)", file).group(2)  # get folio number from file name
        alto_root = etree.parse(f"{dir}/{file}").getroot()
        surface = etree.SubElement(surfaceGrp, "surface", page_attributes(alto_root, dir, folio))
        
        # create <graphic> and assign its attributes
        etree.SubElement(surface, "graphic", url=f"https://gallica.bnf.fr/iiif/ark:/12148/{os.path.basename(dir)}/f{folio}/full/full/0/native.jpg")

        # for every <Page> in this ALTO file, create a <zone> for each <TextBlock> and assign the latter's attributes
        block_att, list_treated_blocks = zone_attributes(alto_root, dir, tag_dict, folio, "PrintSpace/", "TextBlock")
        for i in range(len(list_treated_blocks)):
            text_block = etree.SubElement(surface, "zone", block_att[i])

            # for every <TextBlock> in this ALTO file that has at least one <TextLine>, create a <zone> and assign its attributes
            text_line_att, list_treated_lines = zone_attributes(alto_root, dir, tag_dict, folio, f'TextBlock[@ID="{list_treated_blocks[i]}"]/', "TextLine")
            if len(list_treated_lines) > 0:
                for y in range(len(list_treated_lines)):
                    text_line = etree.SubElement(text_block, "zone", text_line_att[y])

                    # for every <TextLine> in this ALTO file that has a <String>, create a <Line>
                    etree.SubElement(text_line, "line")
            
    
    with open(f'data/{os.path.basename(directory)}.xml', 'wb') as f:
        etree.ElementTree(tei_root).write(f, encoding="utf-8", xml_declaration=True, pretty_print=True)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        directories = [path for path in sys.argv[1:] if os.path.isdir(path)]  # create a list of directories in data/
        for directory in directories:
            #print(f"creating XML-TEI for {os.path.basename(directory)}")
            #print("===============================")
            ordered_files = order_files(directory)
            make_tei(ordered_files, directory)
    else:
        print("No directory given")
