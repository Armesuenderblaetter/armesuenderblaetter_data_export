# creates verticals from xml to import data to NoSketch engine

import os
import glob
import shutil
import re
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
OUTPUT_PATH = "./out"

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
    'l',
    'note',
    'cit',
    'quote',
    'p',
    'imprint',
    'bibl',
    'persName',
    'date',
    'name',
    'head',
    'title',
    'titlePart'
]
# attribs extracted from structures
RELEVANT_ELEMENTS_ATTRIBUTES = [
    "xml:id",
    "type",

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
    "@pos",
    "@ana",
    "@xml:id"
]

# ? what do i do with
# 'rdg'/'lem' has always 'app' as parent
# app can be child of w or top node
# app always contains rdg but not always lem
# 'corr'/sic always in choice but w i sometimes paren, sometimes child

# rdg, app can be always ignored

#
# 'choice': only process sic but try to get textnode of corr


def clean_string(string: str):
    if not string:
        return ""
    cleaned_string = re.sub(
        r"\s+",
        " ",
        string
    )
    cleaned_string = cleaned_string.strip()
    return cleaned_string


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


def create_dirs(output_dir: str) -> None:
    output_dir = os.path.join(output_dir, "verticals")
    shutil.rmtree(output_dir, ignore_errors=True)
    os.makedirs(output_dir, exist_ok=True)


def load_xml_files(input_dir: str) -> list:
    return glob.glob(os.path.join(input_dir, "*.xml"))


def extract_structure_tag(
        element_name,
        attributes=str,
        open=False) -> str:
    if attributes and not open:
        raise ValueError
    if open:
        return f"<{element_name}{attributes}>"
    else:
        return f"</{element_name}>"


def write_to_tsv(output_file: str, verticals: str) -> None:
    with open(output_file, "a", encoding="utf-8") as f:
        f.writelines(verticals)


def mk_docstructure_open(doc: TeiReader) -> str:
    doc_identifier = doc.file.split("/")[-1].removesuffix(".xml")
    delinquent_sexes = doc.any_xpath(
        "//tei:person[@role='delinquent']//tei:sex/@value")
    delinquent_sex = ""
    if "f" in delinquent_sexes and "m" in delinquent_sexes:
        delinquent_sex = "misc"
    elif "f" in delinquent_sexes:
        delinquent_sex = "female"
    else:
        delinquent_sex = "male"
    doc_title = doc.any_xpath(
        "//tei:titleStmt/tei:title/text()"
    )[0].strip()
    doc_title = clean_string(doc_title)
    return " ".join([
        f'<doc id="{doc_identifier}.html"',
        f'delinquent_sexes="{delinquent_sex}"',
        f'title="{doc_title}"',
        'attrs="word lemma type">'
    ])


def get_vocab_info(ref_val: str, element: ET._Element) -> str:
    fs_id = ref_val.strip("# ")
    vocab_state = element.xpath(
        f"//tei:fs[@xml:id='{fs_id}']/tei:f[@name='dictref']/text()",
        namespaces=NS
    )
    if vocab_state:
        return vocab_state[0].strip()
    else:
        return ""


def get_vertical_for_atomic(element, element_name: str) -> str:
    text = clean_string(element.text)
    if element_name == "pc":
        return "<g/>\n" + text
    elif element_name == "w":
        token_attribs = [text]
        for attrib in TOKEN_TAG_ATTRIBUTES:
            val = element.xpath(f"{attrib}", namespaces=NS)
            if val:
                if attrib == "@ana":
                    # val = get_vocab_info(val[0], element)
                    vocab_id = val[0].strip(" #")
                    string_val = global_document_vocab_state[vocab_id]
                else:
                    string_val = clean_string(val[0])
            else:
                string_val = ""
            token_attribs.append(string_val)
        return "\t".join(token_attribs)
    else:
        input(f"unexpected element {element_name}")
        return ""


def get_attributes_from_structure(element):
    attributes = ""
    for attrib in RELEVANT_ELEMENTS_ATTRIBUTES:
        xpath_expression = f"./@{attrib}"
        key = attrib if ":" not in attrib else attrib.split(":")[-1]
        val = element.xpath(xpath_expression, namespaces=NS)
        if val:
            string_val = clean_string(
                val[0]
            )
            attributes += f' {key}="{string_val}"'
    return attributes


def process_element(element, verticals: list):
    ###
    # recursive function to process elements
    ###
    element_name = element.xpath(
        "local-name()").removeprefix("{http://www.tei-c.org/ns/1.0}")
    # elements that get turned into structures
    if element_name in RELEVANT_ELEMENTS:
        attributes = get_attributes_from_structure(element)
        open_structure = extract_structure_tag(
            element_name,
            attributes,
            open=True
        )
        verticals.append(open_structure)
        for subelement in element:
            verticals = process_element(
                verticals=verticals,
                element=subelement
            )
        close_structure = extract_structure_tag(
            element_name,
            open=False,
            attributes=False
        )
        if verticals[-1] == open_structure:
            # happens in some cases due to data complexity,
            # ignores empty structures
            _ = verticals.pop(-1)
        else:
            verticals.append(close_structure)
    # elements dont get transformed into structures
    # but there child-nodes might be relenvant
    elif element_name in CONTAINER_ELEMENTS:
        for subelement in element:
            verticals = process_element(
                verticals=verticals,
                element=subelement
            )
    # elements you need an extra function to deal with
    elif element_name in SPECIAL_ELEMENTS:
        current_function = SPECIAL_ELEMENTS[element_name]
        element = current_function(element)
    # elements that should (hypothetically only
    # contain one and only one textnode as child
    elif element_name in TOKEN_TAGS:
        if element_name == "w":
            verticals.append(
                handle_W(element)
            )
        else:
            vertical = get_vertical_for_atomic(element, element_name)
            verticals.append(vertical)
    # if an element doesn't fit into one of the above categories
    # its name gets logged
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
    global global_document_vocab_state
    for xml_file in tqdm(xml_files, total=len(xml_files)):
        doc = TeiReader(xml_file)
        set_global_vocab_states(doc)
        filename = os.path.splitext(os.path.basename(xml_file))[
            0].replace(".xml", "")
        create_verticals(doc, filename)


global_document_vocab_state = {}


def set_global_vocab_states(doc: TeiReader):
    # this is not pretty, but for performance reasons
    # its better to do it like that
    # using xpath for every single tei:w takes too long
    global global_document_vocab_state
    global_document_vocab_state = {}
    for fs in doc.any_xpath("//tei:fs"):
        fs_id = fs.xpath("@xml:id")[0]
        vocab_state = fs.xpath("tei:f[@name='dictref']/text()", namespaces=NS)
        if vocab_state:
            global_document_vocab_state[fs_id] = vocab_state[0]
        else:
            global_document_vocab_state[fs_id] = ""

    # f"//tei:fs[@xml:id='{fs_id}']/tei:f[@name='dictref']/text()",


if __name__ == "__main__":
    input_filepath = INPUT_PATH
    output_filepath = OUTPUT_PATH
    process_xml_files(input_filepath, output_filepath)
    for name in ignored_elements:
        print(f"ignored {name}")
