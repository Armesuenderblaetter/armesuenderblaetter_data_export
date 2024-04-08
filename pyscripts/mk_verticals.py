# creates verticals from xml to import data to NoSketch engine

import os
import glob
from acdh_tei_pyutils.tei import TeiReader
from acdh_tei_pyutils.utils import extract_fulltext

full_xml_ns = "{http://www.w3.org/1999/xhtml}"
full_tei_ns = "{http://www.tei-c.org/ns/1.0}"


def mk_vertical_from_w(teiw_tag, full_xml_ns):
    # extractable attribute:
    # lemma, ana, pos, id, join, part
    lem_tag = teiw_tag.xpath(
        f"./tei:app/tei:lem",
        namespaces = {
            "tei" : "http://www.tei-c.org/ns/1.0"
        }
    )
    corr_tag = teiw_tag.xpath(
        "./parent::tei:sic/following-sibling::tei:corr",
        namespaces = {
            "tei" : "http://www.tei-c.org/ns/1.0"
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
            root_node=teiw_tag
        )
    lemma = teiw_tag.get('lemma', "no")
    ana = teiw_tag.get('ana', "no")
    pos = teiw_tag.get('pos', "no")
    element_id = teiw_tag.get(
        '{http://www.w3.org/XML/1998/namespace}id',
        ""
    )
    join = teiw_tag.get('join', "no")
    part = teiw_tag.get('part', "no")
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


def export_verticals_from_doc(
    doc: TeiReader,
    title: str,
    doc_id: str,
    date: int
):
    doc_verticals = []
    open_doc_vertical = f'<doc id="{doc_id}" title="{title}" date="{date}">'
    close_doc_vertical = '</doc>\n'
    doc_verticals.append(open_doc_vertical)
    ws = doc.any_xpath("//tei:w")
    for w in ws:
        vertical = mk_vertical_from_w(
            w,
            full_xml_ns=full_xml_ns
        )
        doc_verticals.append(vertical)
    doc_verticals.append(close_doc_vertical)
    return "\n".join(doc_verticals)


def export_verticals_from_doc_bak(
    doc: TeiReader,
    title: str,
    doc_id: str,
    date: int
):
    doc_verticals = []
    open_doc_vertical = f"""<doc id="{doc_id}" attrs="word lemma \\\
        ana pos id join part" title="{title}" date="{date}">"""
    close_doc_vertical = '</doc>\n'
    p_vertical_open = '<p>'
    p_vertical_closed = '</p>'
    lg_vertical_open = "<lg>"
    lg_vertical_close = "</lg>"
    l_vertical_open = "<l>"
    l_vertical_close = "</l>"
    doc_verticals.append(open_doc_vertical)
    structure_elements = doc.any_xpath("//tei:p|//tei:lg")
    if len(structure_elements) != 0:
        for sel in structure_elements:
            sel_name = sel.xpath("local-name()")
            if sel_name == "p":
                doc_verticals.append(p_vertical_open)
                for w in sel.xpath(".//tei:w", namespaces=doc.nsmap):
                    vertical = mk_vertical_from_w(
                        w,
                        full_xml_ns=full_xml_ns
                    )
                    doc_verticals.append(vertical)
                doc_verticals.append(p_vertical_closed)
            elif sel_name == "lg":
                doc_verticals.append(lg_vertical_open)
                for l_element in sel.xpath("./tei:l", namespaces=doc.nsmap):
                    doc_verticals.append(l_vertical_open)
                    for w in l_element.xpath(".//tei:w", namespaces=doc.nsmap):
                        vertical = mk_vertical_from_w(
                            w,
                            full_xml_ns=full_xml_ns
                        )
                        doc_verticals.append(vertical)
                    doc_verticals.append(l_vertical_close)
                doc_verticals.append(lg_vertical_close)
    else:
        input(doc_id)
        for w in doc.any_xpath(".//tei:w"):
            vertical = mk_vertical_from_w(
                w,
                full_xml_ns=full_xml_ns
            )
            doc_verticals.append(vertical)
    doc_verticals.append(close_doc_vertical)
    return "\n".join(doc_verticals)


def get_verticals_from_xml_files(input_filepath):
    # Use glob to get all XML files
    xml_files = glob.glob(
        os.path.join(input_filepath, "*.xml")
    )
    verticals = []
    # Iterate through each XML file
    for xml_file_path in xml_files:
        print(f"processing {xml_file_path}")
        doc = TeiReader(xml_file_path)
        # find all "tei:w" tags
        teiw_tags = doc.any_xpath('.//tei:w')
        # process "tei:w" tags
        doc_verticals = []
        for teiw_tag in teiw_tags:
            full_xml_ns = "{"+doc.ns_xml["xml"]+"}"
            doc_verticals.append(
                mk_vertical_from_w(
                    teiw_tag,
                    full_xml_ns=full_xml_ns
                )
            )
        verticals.append(
            (
                xml_file_path,
                "\n".join(doc_verticals)
            )
        )
    return verticals


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


# if __name__ == "__main__":
#     input_filepath = "./todesurteile_master/303_annot_tei/"
#     output_dir = prepare_output_dir()
#     verticals = get_verticals_from_xml_files(
#         input_filepath
#     )
#     write_verticals_to_file(verticals, output_dir)
