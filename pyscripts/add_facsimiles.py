import os
import glob
import tqdm
import json
from lxml import etree as ET


SOURCE_DIR = os.path.join('asb_master', '303_annot_tei', 'output')
SOURCE_FILE = '*.xml'
source = os.path.join(SOURCE_DIR, SOURCE_FILE)
source_glob = glob.glob(source)

group = dict()

for file in tqdm.tqdm(sorted(source_glob), total=len(source_glob)):
    # group files by witness
    edition = file.split('/')[-1].split('_')[2]
    try:
        add = file.split('/')[-1].split('_')[3]
        if len(add) > 1:
            edition += f"_{add}"
    except IndexError:
        pass
    witness = file.split('/')[-1].split('_')[-1].split('.')[0]
    key = f"{edition}_{witness}"
    if key not in group:
        group[key] = []
    group[key].append(file)

with open('asb_master/facsimiles.json', 'w') as f:
    json.dump(group, f, indent=4)

for file in tqdm.tqdm(sorted(source_glob), total=len(source_glob)):
    # remove existing facsimiles
    doc = ET.parse(file)
    for bad in doc.xpath('.//tei:facsimile',
                         namespaces={"tei": "http://www.tei-c.org/ns/1.0"}):
        bad.getparent().remove(bad)
    witnesses = doc.xpath('.//tei:witness',
                          namespaces={"tei": "http://www.tei-c.org/ns/1.0"})
    facsimile = ET.Element('facsimile')
    edition = file.split('/')[-1].split('_')[2]
    edition_id = file.split('/')[-1].split('_')[1]
    ###############################################################
    # add teiHeader and standOff if they exist in the source file
    ###############################################################
    try:
        source_doc = ET.parse(
            f"./asb_master/303_annot_tei/fb_{edition_id}_{edition}.xml")
    except (FileNotFoundError, OSError):
        print(f"no source file found for {file}")
        source_doc = None
    # teiHeader
    try:
        teiHeader = source_doc.xpath(
            './/tei:teiHeader',
            namespaces={"tei": "http://www.tei-c.org/ns/1.0"})
        header = teiHeader[0]
    except (IndexError, AttributeError):
        print(f"no teiHeader found in {file}")
        header = None
    if header is not None:
        doc.getroot().insert(0, header)
    # standOff
    try:
        standOff = source_doc.xpath(
            './/tei:standOff',
            namespaces={"tei": "http://www.tei-c.org/ns/1.0"})
        standOff = standOff[0]
    except (IndexError, AttributeError):
        print(f"no standOff found in {file}")
        standOff = None
    if standOff is not None:
        doc.getroot().insert(1, standOff)
    # fs
    try:
        doc.xpath(
            './/tei:fs',
            namespaces={"tei": "http://www.tei-c.org/ns/1.0"}
        )[0]
    except (IndexError, AttributeError):
        print(f"no fs found in {file}")
        try:
            fs = source_doc.xpath(
                './/tei:fs',
                namespaces={"tei": "http://www.tei-c.org/ns/1.0"})
            fs[0]
        except (IndexError, AttributeError):
            print(f"no fs found in {file}")
            fs = None
        text = doc.xpath(
            './/tei:text',
            namespaces={"tei": "http://www.tei-c.org/ns/1.0"})[0]
        if fs is not None:
            for f in fs:
                text.insert(1, f)
    ##############################
    # add facsimiles
    ##############################
    try:
        add = file.split('/')[-1].split('_')[3]
        if len(add) > 1:
            edition += f"_{add}"
    except IndexError:
        pass
    current_witness = file.split('/')[-1].split('_')[-1].split('.')[0]
    key = f"{edition}_{current_witness}"
    try:
        pages = group[key]
    except KeyError:
        pages = []
    for page in pages:
        surface = ET.SubElement(facsimile, 'surface')
        surface.attrib['{http://www.w3.org/XML/1998/namespace}id'] = page\
            .split('/')[-1].split('.')[0]
        surface.attrib['type'] = current_witness
        graphic = ET.SubElement(surface, 'graphic')
        graphic.attrib['url'] = f"{page.split('/')[-1].split('.')[0]}.jp2"
    for wit in witnesses:
        xml_id = wit.attrib.get('{http://www.w3.org/XML/1998/namespace}id')
        # switch case statement for xml_id and current_witness
        if xml_id and xml_id != current_witness:
            key = f"{edition}_{xml_id}"
            try:
                pages = group[key]
            except KeyError:
                pages = []
            for page in pages:
                surface = ET.SubElement(facsimile, 'surface')
                surface.attrib[
                    '{http://www.w3.org/XML/1998/namespace}id'] = page\
                    .split('/')[-1].split('.')[0]
                surface.attrib['type'] = xml_id
                graphic = ET.SubElement(surface, 'graphic')
                graphic.attrib[
                    'url'] = f"{page.split('/')[-1].split('.')[0]}.jp2"
        else:
            continue
    doc.getroot().insert(1, facsimile)
    doc.write(file, encoding='utf-8', xml_declaration=True)
