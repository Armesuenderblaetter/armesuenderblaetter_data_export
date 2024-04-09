import glob
from acdh_tei_pyutils.tei import TeiReader

xml_path = "./todesurteile_master/303_annot_tei/*.xml"


def create_ids_for_element(doc: TeiReader, element_name: str):
    doc_id = xml_doc.any_xpath('//tei:TEI/@xml:id')[0].removesuffix(".xml")
    xml_namespace = f'{{{xml_doc.ns_xml.get("xml")}}}'
    i = 0
    for element in doc.any_xpath(f"//tei:body//tei:{element_name}"):
        i += 1
        element_id = "{}_{}_{:04}".format(doc_id, element_name, i)
        element.set(xml_namespace + "id", element_id)


print("Adding ids to p and l emlements")
for xml_filepath in glob.glob(xml_path):
    xml_doc = TeiReader(xml_filepath)
    create_ids_for_element(xml_doc, "p")
    create_ids_for_element(xml_doc, "l")
    xml_doc.tree_to_file(xml_filepath)
print("Done")
