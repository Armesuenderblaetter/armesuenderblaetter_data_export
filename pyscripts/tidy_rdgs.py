import glob
import lxml.etree as etree
import lxml.builder as builder
from acdh_tei_pyutils.tei import TeiReader

xmlns = "http://www.w3.org/XML/1998/namespace"

tei_nsmp = {
    "tei": "http://www.tei-c.org/ns/1.0",
    "xml": xmlns
}

# # xml factory
teiMaker = builder.ElementMaker(
    namespace="http://www.tei-c.org/ns/1.0",
    nsmap=tei_nsmp
)


class Witness:
    def __init__(
        self,
        element: etree._Element,
        counter: int,
        primary_wit_id: str
    ):
        self.counter = counter
        self.element = element
        self.id = element.xpath(
            "./@xml:id",
            namespaces=tei_nsmp
        )[0].strip()
        if primary_wit_id != "" and self.id == primary_wit_id:
            self.type = "primary"
        elif counter == 0 and primary_wit_id == "":
            self.type = "primary"
        else:
            self.type = "secondary"
        self.element.attrib["type"] = self.type
        self.institution = self.element.xpath(
            "./tei:msDesc/tei:msIdentifier/tei:institution/text()",
            namespaces=tei_nsmp
        )[0].strip()
        self.type_pbs()

    def type_pbs(self):
        own_pbs = self.element.xpath(
            f"//tei:pb[@edRef='#{self.id}']",
            namespaces=tei_nsmp
        )
        for opb in own_pbs:
            opb.attrib["type"] = self.type


def extract_witnesses(doc: TeiReader) -> list:
    witness_elements = doc.any_xpath(
        "//tei:listWit/tei:witness"
    )
    witness_objs = []
    try:
        primary_wit_id = doc.any_xpath(
            "//tei:app/tei:lem/@wit"
        )[0].strip(" #")
    except IndexError:
        primary_wit_id = ""
    c = 0
    for w_el in witness_elements:
        current_w = Witness(w_el, c, primary_wit_id)
        witness_objs.append(current_w)
        c += 1
    witness_objs.sort(key=lambda w: w.counter)
    return witness_objs


def link_unlinked_readings(doc: TeiReader, witnesses: list):
    primary = witnesses[0]
    other_witnesses = witnesses[1:]
    local_name = "local-name()='rdg' or local-name()='lem'"
    elem_condition = f"[({local_name}) and not(@wit)]"
    for app in doc.any_xpath(
        f"//tei:app[tei:*{elem_condition}]"
    ):
        for lem in app.xpath("./tei:lem", namespaces=tei_nsmp):
            lem.attrib["wit"] = f"#{primary.id}"
        rdgs = app.xpath("./tei:rdg", namespaces=tei_nsmp)
        rdg_counter = 0
        for w in other_witnesses:
            try:
                current_rdg = rdgs[rdg_counter]
                current_rdg.attrib["wit"] = f"#{w.id}"
            except IndexError:
                print("\n"*2)
                print(
                    etree.tostring(
                        w.element.getparent()
                    ).decode()
                )
                print(
                    etree.tostring(
                        app
                    ).decode()
                )
                raise IndexError


def create_ids_for_apps(doc):
    counter = 0
    for app in doc.any_xpath("//tei:app"):
        counter += 1
        app.attrib[f"{{{tei_nsmp['xml']}}}id"] = f"app_{counter}"
    counter = 0
    for rdg in doc.any_xpath("//tei:rdg"):
        counter += 1
        rdg.attrib[f"{{{tei_nsmp['xml']}}}id"] = f"rdg_{counter}"
    for lem in doc.any_xpath("//tei:lem"):
        counter += 1
        rdg.attrib[f"{{{tei_nsmp['xml']}}}id"] = f"lem_{counter}"
# def relink_linked_readings(doc: TeiReader, witnesses: list):
#     primary = witnesses[0]
#     other_witnesses = witnesses[1:]
#     for lem in doc.any_xpath(
#         "//tei:app/tei:lem[@wit]"
#     ):
#         if lem.attrib["wit"] != f"#{primary.id}":
#             input(lem.attrib["wit"])


def tidy_readings(doc: TeiReader):
    witnesses = extract_witnesses(doc)
    if witnesses:
        link_unlinked_readings(doc, witnesses)
        create_ids_for_apps(doc)
    if not witnesses:
        for pb in doc.any_xpath(".//tei:pb"):
            pb.attrib["type"] = "primary"
        list_wit = teiMaker.listWit(
            "\n",
            teiMaker.witness(
                type="primary"
            ),
            "\n"
        )
        wit_content = doc.any_xpath("//tei:sourceDesc/*")
        if len(wit_content) > 2:
            raise ValueError
        wit_content[0].addprevious(list_wit)
        for x in wit_content:
            list_wit[0].append(x)


testpath = "./todesurteile_master/303_annot_tei/*.xml"
if __name__ == "__main__":
    xml_path = testpath
    for path in glob.glob(xml_path):
        doc = TeiReader(path)
        tidy_readings(doc)
