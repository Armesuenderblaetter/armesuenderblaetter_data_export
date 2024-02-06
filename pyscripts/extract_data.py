import glob
import re
import lxml
from acdh_tei_pyutils.tei import TeiReader
from acdh_baserow_pyutils import BaseRowClient
cases_dir = "./todesurteile_master/303_annot_tei/*.xml"
error_docs = {}



for file_path in glob.glob(cases_dir):
    print(file_path)
    try:
        tei_doc = TeiReader(file_path)
    except lxml.etree.XMLSyntaxError as err:
        error_docs[file_path] = err
        continue
    doc_id = re.match(".*?/([^/]+).xml", file_path).group(1)
    print(doc_id)

if error_docs:
    print(f"\n\n{len(error_docs)} faulty docs:")
    for doc, err in error_docs.items():
        print(f"{doc}:\t{err}")