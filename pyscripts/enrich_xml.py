import os
import glob
import tqdm
import json
from lxml import etree as ET


UNSPLIT_SOURCE_DIR = os.path.join('asb_master', '303_annot_tei')
SOURCE_DIR = os.path.join('asb_master', '303_annot_tei', 'output')
SOURCE_FILE = '*.xml'
NSMAP = {"tei": "http://www.tei-c.org/ns/1.0"}

source = os.path.join(SOURCE_DIR, SOURCE_FILE)
source_glob = glob.glob(source)


def yield_files(source_glob: str) -> iter:
    for file in tqdm.tqdm(sorted(source_glob), total=len(source_glob)):
        yield file


def create_witness_dict(files: iter, debug: bool = False) -> dict:
    """_summary_

    Args:
        files (iter): iterator of source XML files
        debug (bool, optional): if True, writes the witness dictionary
        to a JSON file. Defaults to False.

    Returns:
        dict: key: edition_witness, value: list of facsimile files (glob)
    """
    group = dict()
    for file in files:

        # ex: fb_303_edition1_witness1.xml -> edition1
        edition = file.split('/')[-1].split('_')[2]
        try:
            # ex: fb_303_edition1_info_witness1.xml -> edition1_info
            add = file.split('/')[-1].split('_')[3]
            if len(add) > 1:
                edition += f"_{add}"
        except IndexError:
            pass

        # example: fb_303_edition1_witness1.xml -> witness1
        witness = file.split('/')[-1].split('_')[-1].split('.')[0]

        # example: edition1_witness1
        key = f"{edition}_{witness}"
        if key not in group:
            group[key] = []
        group[key].append(file)

    if debug:
        with open('asb_master/facsimiles.json', 'w') as f:
            json.dump(group, f, indent=4)
    return group


def update_xml_node(
    source_doc: ET.ElementTree,
    doc: ET.ElementTree | ET.Element,
    xpath: str,
    file: str,
    idx: int = 0
) -> None:
    """_summary_

    Args:
        doc (ET.ElementTree): _description_
        xpath (str): _description_
        file (str): _description_
        idx (int): _description_
    """
    try:
        node = source_doc.xpath(
            xpath,
            namespaces=NSMAP)
        if len(node) == 1:
            node = node[0]
        else:
            node[0]
    except (IndexError, AttributeError):
        print(f"no node found in {file}")
        node = None
    if node is not None:
        if isinstance(doc, ET.ElementTree):
            doc.getroot().insert(idx, node)
        else:
            for n in node:
                doc.insert(idx, n)


def add_surfaces(
    pages: list[str],
    facsimile: ET.Element,
    witness: str
) -> None:
    """_summary_

    Args:
        pages (list[str]): _description_
        facsimile (ET.Element): _description_
        witness (str): _description_
    """
    for page in pages:
        surface = ET.SubElement(facsimile, 'surface')
        surface.attrib[
            '{http://www.w3.org/XML/1998/namespace}id'] = page\
            .split('/')[-1].split('.')[0]
        surface.attrib['type'] = witness
        graphic = ET.SubElement(surface, 'graphic')
        graphic.attrib[
            'url'] = f"{page.split('/')[-1].split('.')[0]}.jp2"


def enrich_xml(files: iter, group: dict):
    """_summary_

    Args:
        files (iter): _description_
        group (dict): _description_
    """
    for file in files:

        doc = ET.parse(file)
        for bad in doc.xpath('.//tei:facsimile|.//tei:standOff',
                             namespaces=NSMAP):
            bad.getparent().remove(bad)

        witnesses = doc.xpath('.//tei:witness', namespaces=NSMAP)
        facsimile = ET.Element('facsimile')
        edition = file.split('/')[-1].split('_')[2]
        edition_id = file.split('/')[-1].split('_')[1]

        # loading source doc = unsplit xml to get
        # teiHeader, standOff and fs
        try:
            source_doc = ET.parse(
                os.path.join(UNSPLIT_SOURCE_DIR,
                             f"fb_{edition_id}_{edition}.xml"))
        except (FileNotFoundError, OSError):
            print(f"no source file found for {file}")
            source_doc = None

        if source_doc is not None:
            # teiHeader
            update_xml_node(source_doc, doc, './/tei:teiHeader', file, idx=0)
            # standOff
            # update_xml_node(source_doc, doc, './/tei:standOff', file, idx=1)
            # fs
            try:
                # last page already contains tei:fs skipping
                doc.xpath(
                    './/tei:fs',
                    namespaces=NSMAP
                )[0]
            except (IndexError, AttributeError):
                print(f"no fs found in {file}, adding from source")
                text = doc.xpath(
                    './/tei:text',
                    namespaces=NSMAP)[0]
                update_xml_node(source_doc, text, './/tei:fs', file, idx=1)

        # ex: fb_303_edition1_witness1.xml -> edition1_info_witness1
        try:
            add = file.split('/')[-1].split('_')[3]
            if len(add) > 1:
                edition += f"_{add}"
        except IndexError:
            print(f"no additional edition info found for {file}")
            pass
        current_witness = file.split('/')[-1].split('_')[-1].split('.')[0]
        key = f"{edition}_{current_witness}"

        try:
            pages = group[key]
        except KeyError:
            print(f"no pages found for {file} with key {key}")
            pages = []

        add_surfaces(pages, facsimile, current_witness)

        # adding surfaces for other witnesses in the same edition
        for wit in witnesses:
            xml_id = wit.attrib.get('{http://www.w3.org/XML/1998/namespace}id')

            if xml_id and xml_id != current_witness:
                key = f"{edition}_{xml_id}"

                try:
                    pages = group[key]
                except KeyError:
                    pages = []

                add_surfaces(pages, facsimile, xml_id)
            else:
                continue

        doc.getroot().insert(1, facsimile)
        doc.write(file, encoding='utf-8', xml_declaration=True)
    return "completed"


def main():
    group = create_witness_dict(yield_files(source_glob), debug=True)
    finsihed = enrich_xml(yield_files(source_glob), group)
    print(f"enrichment {finsihed}")


if __name__ == "__main__":
    main()
