# creates verticals from xml to import data to NoSketch engine

import os
import glob
import shutil
from lxml import etree as ET
from tqdm import tqdm
from acdh_tei_pyutils.tei import TeiReader
from acdh_tei_pyutils.utils import extract_fulltext

morph_keys = [
    'Case',
    'Definite',
    'Degree',
    'Foreign',
    'Gender',
    'Mood',
    'Number',
    'Person',
    'Poss',
    'PronType',
    'Reflex',
    'Tense',
    'VerbForm'
]

ignored_elements = []
INPUT_PATH = "./todesurteile_master/303_annot_tei"
OUTPUT_PATH = "./out/verticals"

NS = {
    "tei": "http://www.tei-c.org/ns/1.0",
    "xml": "http://www.w3.org/XML/1998/namespace"
}

# elements which child elements get processed and
# that get converted into vertical structures
RELEVANT_ELEMENTS = [
    'placeName',
    'abbr',
    'lg',
    'note',
    'cit',
    'quote',
    'p',
    'imprint',
    'l',
    'bibl',
    'persName',
    'div',
    'date',
    'name',
    'head',
    'title',
    'titlePart'
]
# attribs extracted from structures
RELEVANT_ELEMENTS_ATTRIBUTES = [
    "xml:id"
]

# elements which child elements get processed and
# that DON'T get converted into vertical structures
CONTAINER_ELEMENTS = [
    "div",
    'seg',
    'pubPlace',
    'corr'
    'sic',
    'ref',
    'rendition',
    'rs',
    'said',
    'publisher',
    'unclear',
    "closer",
    'hi',
    'q',
    'imprimatur',
    'item',
    'list',
    "lem",
    "app",
    "unclear",
    "hi"
]
# other elements are completely ignored ar

# tags considered tokens
TOKEN_TAGS = [
    "w",
    "pc"
]

TOKEN_TAG_ATTRIBUTES = [
    "@lemma",
    "@pos"
]

# ? what do i do with
# 'rdg'/'lem' has always 'app' as parent
# app can be child of w or top node
# app always contains rdg but not always lem
# 'corr'/sic always in choice but w i sometimes paren, sometimes child

# rdg, app can be always ignored

#
# 'choice': only process sic but try to get textnode of corr


def handle_parent_choice(choice) -> ET._Element:
    w_tags = choice.xpath(".//tei:w", namespaces=NS)
    try:
        wtag = w_tags[0]
    except IndexError:
        input(ET.tostring(choice.getparent().getparent().getparent()).decode())
    return wtag


def handle_parent_app(app) -> ET._Element:
    w_tags = app.xpath(".//tei:w", namespaces=NS)
    return w_tags[0]


SPECIAL_ELEMENTS = {
    "choice": handle_parent_choice,
    "app": handle_parent_app
}


def handle_W(w) -> str:
    if w.xpath(".//tei:choice/tei:corr", namespaces=NS):
        w.text = extract_fulltext(
            w.xpath(".//tei:choice/tei:corr", namespaces=NS)[0]
        )
    elif w.xpath("./tei:hi", namespaces=NS):
        w.text = extract_fulltext(w)
    elif w.xpath("./tei:unclear", namespaces=NS):
        w.text = extract_fulltext(w)
    elif w.xpath(".//tei:app/tei:lem", namespaces=NS):
        w.text = extract_fulltext(
            w.xpath(".//tei:lem", namespaces=NS)[0]
        )
    elif (w.xpath(
            ".//tei:app/tei:rdg", namespaces=NS
        ) and not (w.text and w.text.strip())
    ):
        w.text = extract_fulltext(
            w.xpath(".//tei:rdg", namespaces=NS)[0]
        )
    elif w.xpath(".//*"):
        w.text = extract_fulltext(w)
    for x in w:
        w.remove(x)
    return get_vertical_for_atomic(w, "w")

# 'app',
# 'supplied'


def create_dirs(output_dir: str) -> None:
    output_dir = os.path.join(output_dir, "verticals")
    shutil.rmtree(output_dir, ignore_errors=True)
    os.makedirs(output_dir, exist_ok=True)


def load_xml_files(input_dir: str) -> list:
    return glob.glob(os.path.join(input_dir, "*.xml"))


def extract_structure_tag(
        element_name,
        attributes: dict = {},
        open=False) -> str:
    if attributes and not open:
        raise ValueError
    if open:
        return f"<{element_name}>"
    else:
        return f"</{element_name}>"


def write_to_tsv(output_file: str, verticals: str) -> None:
    with open(output_file, "a", encoding="utf-8") as f:
        f.writelines(verticals)


def mk_docstructure_open(doc: TeiReader) -> str:
    # not_before = doc.any_xpath(
    # "//tei:msDesc/tei:history/tei:origin/@notBefore-iso")[0].strip()
    # not_after = doc.any_xpath(
    # "//tei:msDesc/tei:history/tei:origin/@notAfter-iso")[0].strip()
    # doc_year = not_before.split("-")[0].strip()
    # doc_title = doc.any_xpath(
    # "//tei:titleStmt/tei:title/text()")[0].strip()
    # doc_id = doc.any_xpath("//tei:TEI/@xml:id")[0].strip()
    # xml_status = doc.any_xpath("//tei:revisionDesc/@status")[0].strip()
    # doc_type = doc.any_xpath(
    # "//tei:physDesc/tei:objectDesc/@form")[0].strip()
    # doc_text_type = doc.any_xpath("//tei:text/@type")[0].strip()
    # dataset = doc.any_xpath(
    # "//tei:idno[@type='bv_data_set']/text()")[0].strip()
    # if dataset == "Datenset A":
    #     dataset = "Gesetzestexte & Entwürfe"
    # elif dataset == "Datenset B":
    #     dataset = "Sitzungsprotokolle"
    # else:
    #     dataset = "sonstige"
    # return " ".join([
    #     f'<doc id="{doc_id}"',
    #     f'document_title="{doc_title}"',
    #     f'created_not_before="{not_before}"',
    #     f'created_not_after="{not_after}"',
    #     f'creation_year="{doc_year}"',
    #     f'state_of_correction="{xml_status}"',
    #     f'document_type="{doc_type}"',
    #     f'text_type="{doc_text_type}"',
    #     f'dataset="{dataset}"',
    #     f'attrs="word lemma type">'
    # ])
    return "<doc>"


def handle_ana_attribute(element) -> str:
    ana = element.xpath("@ana[normalize-space()!='']")
    if ana:
        return ana[0]
    return ""


def get_vertical_for_atomic(element, element_name: str) -> str:
    text = element.text.strip()
    if element_name == "pc":
        return "<g/>\n" + text
    elif element_name == "w":
        token_attribs = [text]
        for attrib in TOKEN_TAG_ATTRIBUTES:
            val = element.xpath(f"{attrib}")
            string_val = val[0] if val else ""
            token_attribs.append(string_val)
        token_attribs.append(
            handle_ana_attribute(
                element
            )
        )
        return "\t".join(token_attribs)
    else:
        input(f"unexpected element {element_name}")
        return ""


def get_attributes_from_structure(element):
    return_dict = {}
    for attrib in RELEVANT_ELEMENTS_ATTRIBUTES:
        val = element.xpath(f"./@{attrib}", namespaces=NS)
        return_dict[attrib] = val


def process_element(element, verticals: list):
    element_name = element.xpath(
        "local-name()").removeprefix("{http://www.tei-c.org/ns/1.0}")
    if element_name in RELEVANT_ELEMENTS:
        # if element_name == "head":
        #         input(element_name)
        attributes = get_attributes_from_structure(element)
        open_structure = extract_structure_tag(
            element_name,
            attributes,
            open=True
        )
        verticals.append(open_structure)
        for subelement in element:
            # input(subelement)
            verticals = process_element(
                verticals=verticals,
                element=subelement
            )
        # input(element_name)
        close_structure = extract_structure_tag(
            element_name,
            open=False
        )
        verticals.append(close_structure)
        # if element_name == "head":
        #         input(verticals)
    elif element_name in CONTAINER_ELEMENTS:
        for subelement in element:
            verticals = process_element(
                verticals=verticals,
                element=subelement
            )
    elif element_name in SPECIAL_ELEMENTS:
        current_function = SPECIAL_ELEMENTS[element_name]
        element = current_function(element)
    elif element_name in TOKEN_TAGS:
        if element_name == "w":
            verticals.append(
                handle_W(element)
            )
        else:
            vertical = get_vertical_for_atomic(element, element_name)
            # print(vertical)
            verticals.append(vertical)
    else:
        if element_name not in ignored_elements:
            ignored_elements.append(element_name)
    return verticals


def create_verticals(doc: TeiReader, output_filename) -> None:
    verticals = []
    docstructure_opening = mk_docstructure_open(doc)
    verticals.append(docstructure_opening)
    roots = doc.any_xpath("//tei:body/*")
    for root in roots:
        verticals += process_element(
            verticals=[],
            element=root
        )
    docstructure_closing = "</doc>\n"
    verticals.append(docstructure_closing)
    verticals_str = "\n".join(verticals)
    output_file = os.path.join(
        output_filepath, "verticals", f"{output_filename}.tsv")
    write_to_tsv(output_file, verticals_str)


def process_xml_files(input_dir: str, output_dir: str) -> None:
    create_dirs(output_dir)
    xml_files = load_xml_files(input_dir)
    for xml_file in tqdm(xml_files, total=len(xml_files)):
        doc = TeiReader(xml_file)
        filename = os.path.splitext(os.path.basename(xml_file))[
            0].replace(".xml", "")
        print(filename)
        create_verticals(doc, filename)


if __name__ == "__main__":
    input_filepath = INPUT_PATH
    output_filepath = OUTPUT_PATH
    process_xml_files(input_filepath, output_filepath)
    for name in ignored_elements:
        print(f"ignored {name}")
