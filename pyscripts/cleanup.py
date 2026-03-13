import glob
import os
import tqdm
import shutil


NS = [
    'xmlns="http://www.tei-c.org/ns/1.0"',
    '{http://www.w3.org/XML/1998/namespace}'
]
NSMAP = {
    "tei": "http://www.tei-c.org/ns/1.0",
    "xml": "http://www.w3.org/XML/1998/namespace"
}

# Remove the original file
# After the split it is not required anymore
# SOURCE_FILE = '*.xml'
# SOURE_PATH = glob.glob(os.path.join('data',
#                                     'editions_modified', SOURCE_FILE))
# os.remove(SOURE_PATH)

MODIFIED_DIR = 'asb_master/303_annot_tei_modified'
INPUT_DIR = 'output'
INPUT_PROJECT_DIR = '*'
OUTPUT_DIR = os.path.join('asb_master', '303_annot_tei')

files = os.path.join(INPUT_DIR, INPUT_PROJECT_DIR, '*.xml')
files_glob = glob.glob(files)


def file_parser(file) -> str:
    with open(file, 'r') as f:
        text = f.read()
    return text


def replace_namespace(text) -> str:
    for ns in NS:
        if ns == '{http://www.w3.org/XML/1998/namespace}':
            text = text.replace(ns, 'xml:')
        else:
            text = text.replace(ns, '')
    return text


def add_root_namesapce(text) -> str:
    text = text.replace(
        '<TEI',
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"')
    return text


if __name__ == '__main__':
    debug = False
    for file in tqdm.tqdm(files_glob, total=len(files_glob)):
        text = file_parser(file)
        text = replace_namespace(text)
        text = add_root_namesapce(text)
        os.makedirs(os.path.join(OUTPUT_DIR, "output"), exist_ok=True)
        delete_path = output_path = os.path.join(
            OUTPUT_DIR,
            f"{os.path.dirname(file).split("/")[1]}_{os.path.basename(file)}")
        if os.path.exists(delete_path):
            os.remove(delete_path)
        output_path = os.path.join(
            OUTPUT_DIR,
            "output",
            f"{os.path.dirname(file).split("/")[1]}_{os.path.basename(file)}")
        with open(output_path, 'w') as f:
            f.write(text)
    if not debug:
        shutil.rmtree(INPUT_DIR)
        shutil.rmtree(MODIFIED_DIR)
