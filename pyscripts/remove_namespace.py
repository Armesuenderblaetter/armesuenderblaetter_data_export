import glob
import os
import tqdm
from acdh_tei_pyutils.tei import TeiReader


SOURCE_DIR = 'asb_master/303_annot_tei'
SOURCE_FILE = '*.xml'
source = os.path.join(SOURCE_DIR, SOURCE_FILE)
source_glob = glob.glob(source)

NS = [
    ' xmlns="http://www.tei-c.org/ns/1.0"'
]

NSMAP = {
    "tei": "http://www.tei-c.org/ns/1.0",
    "xml": "http://www.w3.org/XML/1998/namespace",
}


def file_parser(file):
    with open(file, 'r') as f:
        text = f.read()
    return text


def replace_namespace(text):
    for ns in NS:
        text = text.replace(ns, '')
    return text


def save_file(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(text)


def add_id_to_pb(file):
    doc = TeiReader(file)
    file = file.replace('.xml', '_pb.xml')
    pb = doc.any_xpath('//tei:pb')
    for i, p in enumerate(pb):
        facs = p.attrib.get('facs')
        if facs is not None:
            facs_id = facs.replace('.jp2', '')
            facs_id = facs_id.split('_')
            facs_id = f"{facs_id[2]}_{facs_id[3]}"
            p.attrib['source'] = facs_id
        else:
            p.attrib['source'] = f"pb_{i+1:04d}"
    doc.tree_to_file(file)
    return file


if __name__ == '__main__':
    for file in tqdm.tqdm(source_glob, total=len(source_glob)):
        file = add_id_to_pb(file)
        text = file_parser(file)
        text = replace_namespace(text)
        output_path = os.path.join(f"{SOURCE_DIR}_modified",
                                   os.path.basename(file.replace('_pb', '')))
        save_file(output_path, text)
        os.remove(file)
