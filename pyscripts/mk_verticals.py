# creates verticals from xml to import data to NoSketch engine

import os
from acdh_tei_pyutils.tei import TeiReader
from acdh_tei_pyutils.utils import extract_fulltext

full_xml_ns = "{http://www.w3.org/1999/xhtml}"
xml_id_name = '{http://www.w3.org/XML/1998/namespace}id'


def get_id(element):
    return element.get(
        xml_id_name,
        ""
    )


def mk_vertical_from_element(element):
    # extractable attribute:
    # lemma, ana, pos, id, join, part
    lem_tag = element.xpath(
        "./tei:app/tei:lem",
        namespaces={
            "tei": "http://www.tei-c.org/ns/1.0"
        }
    )
    corr_tag = element.xpath(
        "./parent::tei:sic/following-sibling::tei:corr",
        namespaces={
            "tei": "http://www.tei-c.org/ns/1.0"
        }
    )
    if lem_tag:
        text = extract_fulltext(
            root_node=lem_tag[0]
        )
    elif corr_tag:
        text = extract_fulltext(
            root_node=corr_tag[0]
        )
    else:
        text = extract_fulltext(
            root_node=element
        )
    lemma = element.get('lemma', "no")
    ana = element.get('ana', "no")
    pos = element.get('pos', "no")
    element_id = get_id(element)
    join = element.get('join', "no")
    part = element.get('part', "no")
    vertical = '\t'.join(
        [
            text,
            lemma,
            ana,
            pos,
            element_id,
            join,
            part
        ]
    )
    return vertical


def process_lg(lg_element, nsmap) -> list:
    verticals = []
    verticals.append(
        f"<lg type='{lg_element.get('type', '')}'>"
    )
    for sub_lg in lg_element.xpath("./tei:lg", namespaces=nsmap):
        verticals += process_lg(
            sub_lg,
            nsmap
        )
    for l_element in lg_element.xpath("./tei:l", namespaces=nsmap):
        verticals.append(
            f"<l id={get_id(l_element)}>"
        )
        for w in l_element.xpath(".//tei:w", namespaces=nsmap):
            vertical = mk_vertical_from_element(w)
            verticals.append(vertical)
        verticals.append("</l>")
    verticals.append("</lg>")
    return verticals


attrs = "word lemma ana pos id join part"


def export_verticals_from_doc(
    doc: TeiReader,
    title: str,
    doc_id: str,
    date: int
):
    doc_verticals = []
    attribs = f'id="{doc_id}.html" attrs="{attrs}"'
    attribs += f'title="{title}" date="{date}"'
    open_doc_vertical = f"<doc {attribs}>"
    close_doc_vertical = '</doc>\n'
    doc_verticals.append(open_doc_vertical)
    structure_elements = doc.any_xpath("//tei:p|//tei:lg[not(parent::tei:lg)]")
    if len(structure_elements) != 0:
        for sel in structure_elements:
            sel_name = sel.xpath("local-name()")
            if sel_name == "p":
                doc_verticals.append(
                    f"<p id={get_id(sel)}>"
                )
                for content_el in sel.xpath(
                    ".//tei:w|.//tei:pc", namespaces=doc.nsmap
                ):
                    if content_el.tag == "{http://www.tei-c.org/ns/1.0}pc":
                        glue = "<g/>"
                        doc_verticals.append(glue)
                        vertical = mk_vertical_from_element(content_el)
                        doc_verticals.append(vertical)
                    else:
                        vertical = mk_vertical_from_element(content_el)
                        doc_verticals.append(vertical)
                doc_verticals.append('</p>')
            elif sel_name == "lg":
                doc_verticals += process_lg(
                    lg_element=sel,
                    nsmap=doc.nsmap
                )
    else:
        input(doc_id)
        for w in doc.any_xpath(".//tei:w"):
            vertical = mk_vertical_from_element(w)
            doc_verticals.append(vertical)
    doc_verticals.append(close_doc_vertical)
    return "\n".join(doc_verticals)


def write_verticals_to_file(verticals, output_dir):
    # Write the verticals list to a TSV file
    for xml_file_path, verticals_string in verticals:
        output_file = os.path.join(
            output_dir, os.path.splitext(
                os.path.basename(
                    xml_file_path
                )
            )[0] + ".tsv"
        )
        with open(output_file, "w", encoding="utf-8") as f:
            print(f"writing to {output_file}")
            f.write(verticals_string)


def prepare_output_dir(output_filepath="./out/"):
    # create dir for output files
    output_dir = os.path.join(output_filepath, "verticals")
    print(f"output to {output_dir}")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir
