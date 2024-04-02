# creates verticals from xml to import data to NoSketch engine

import os
import glob
from acdh_tei_pyutils.tei import TeiReader
from acdh_tei_pyutils.utils import extract_fulltext

full_xml_ns = ""

def mk_vertical_from_w(teiw_tag, full_xml_ns):
    # extractable attribute:
    # lemma, ana, pos, id, join, part
    text = extract_fulltext(teiw_tag)
    lemma = teiw_tag.get('lemma', "")
    ana = teiw_tag.get('ana', "")
    pos = teiw_tag.get('pos', "")
    element_id = teiw_tag.get(
        f"{full_xml_ns}id",
        ""
    )
    join = teiw_tag.get('join', "")
    part = teiw_tag.get('part', "")
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
            full_xml_ns="{"+doc.ns_xml["xml"]+"}"
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

def prepare_output_dir(output_filepath):
    # create dir for output files
    output_dir = os.path.join(output_filepath, "verticals")
    print(f"output to {output_dir}")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

if __name__ == "__main__":
    input_filepath = "./todesurteile_master/303_annot_tei/"
    output_filepath = "./verticalstest"
    output_dir = prepare_output_dir(output_filepath)
    verticals = get_verticals_from_xml_files(
        input_filepath
    )
    write_verticals_to_file(verticals, output_dir)
