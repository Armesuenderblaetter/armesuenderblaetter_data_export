# creates verticals from xml to import data to NoSketch engine

import os
import glob
from acdh_tei_pyutils.tei import TeiReader
from acdh_tei_pyutils.utils import extract_fulltext

def process_xml_files(input_filepath, output_filepath):
    # create dir for output files
    output_dir = os.path.join(output_filepath, "verticals")
    os.makedirs(output_dir, exist_ok=True)
    
    # Use glob to get all XML files
    xml_files = glob.glob(os.path.join(input_filepath, "*.xml"))
    
    # Iterate through each XML file
    for xml_file_path in xml_files:
        doc = TeiReader(xml_file_path)
        # find all "tei:w" tags
        teiw_tags = doc.any_xpath('.//tei:w')
        # process "tei:w" tags
        for teiw_tag in teiw_tags:
            verticals = []
            # extractable attribute: 
            # lemma, ana, pos, id, join, part
            text = extract_fulltext(teiw_tag)
            lemma = teiw_tag.get('lemma', "")
            ana = teiw_tag.get('ana', "")
            pos = teiw_tag.get('pos', "")
            element_id = teiw_tag.get('id', "")
            join = teiw_tag.get('join', "")
            part = teiw_tag.get('part', "")
            verticals.append(
                '\t'.join(
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
            )
            # Write the verticals list to a TSV file
            output_file = os.path.join(
                output_dir, os.path.splitext(
                    os.path.basename(
                        xml_file_path
                    )
                )[0] + ".tsv"
            )
            with open(output_file, "a", encoding="utf-8") as f:
                f.write('\t'.join(verticals) + '\n')

if __name__ == "__main__":
    input_filepath = "./todesurteile_master/303_annot_tei/"
    output_filepath = "./verticalstest"
    process_xml_files(input_filepath, output_filepath)
