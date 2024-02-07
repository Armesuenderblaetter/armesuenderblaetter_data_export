import glob
import re
import lxml
from lxml import etree
from acdh_tei_pyutils.tei import TeiReader
from acdh_baserow_pyutils import BaseRowClient
cases_dir = "./todesurteile_master/303_annot_tei/*.xml"
error_docs = {}

all_missing_fields = []
events_with_missing_field = 0

class Event:
    regulary_missing_fields = [
        "tools",
        "date",
        "element"
    ]

    def __init__(
            self,
            type:list,
            id:list,
            date:list,
            place:list,
            description:list,
            offences:list,
            tools:list,
            xml_element: etree._Element,
            filepath:str) -> None:
        self.type: str = type[0] if type else ""
        self.id: str = id[0] if id else ""
        self.date: str = date[0] if date else ""
        self.place: str = place[0] if place else ""
        self.description: str = description[0] if description else ""
        self.offences: list = offences
        self.tools: list = tools
        self.element: etree._Element = xml_element
        self.source_file_path: str = filepath


    def print_source(self):
        print(
            etree.tostring(
                self.element
            ).decode()
        )


    def check_4_empty_fields(self):
        global all_missing_fields
        global events_with_missing_field
        missing_vals = [field for field, val in vars(self).items() if (not field in Event.regulary_missing_fields and not bool(val))]
        all_missing_fields += missing_vals
        if missing_vals:
            events_with_missing_field += 1
            print(f"\nmissing: {', '.join(missing_vals)}")
            print("\nsource:")
            self.print_source()


def extract_offences(doc:TeiReader, file_path: str):
    events = []
    for event_element in doc.any_xpath(".//tei:listEvent[@type='offences']/tei:event"):
        event_type: list = event_element.xpath("./@type", namespaces=doc.nsmap)
        #  if more then 1 person is associtated with the event it just gets referenced, while data are doublicated (?)
        xml_id: list = event_element.xpath("./@xml:id|./@ref", namespaces=doc.nsmap)
        # desc cant contain:
        # desc', 'ref', 'trait', 'placeName', 'date'
        date: list = event_element.xpath("./tei:desc/tei:date/@when", namespaces=doc.nsmap)
        place: list = event_element.xpath("./tei:desc/tei:placeName/text()[1]", namespaces=doc.nsmap)
        description_str: list = event_element.xpath("./tei:desc/tei:desc/text()[1]", namespaces=doc.nsmap)
        typed_offences: list = event_element.xpath("./tei:desc/tei:trait[@type='typeOfOffence']/tei:desc/tei:list/tei:item/text()", namespaces=doc.nsmap)
        typed_tools: list = event_element.xpath("./tei:desc/tei:trait[@type='toolOfCrime']/tei:desc/text()", namespaces=doc.nsmap)
        events.append(Event(event_type, xml_id, date, place, description_str, typed_offences, typed_tools, event_element, file_path))
    return events

events = []

for file_path in glob.glob(cases_dir):
    print(f"\n\n{file_path}")
    try:
        tei_doc = TeiReader(file_path)
        events += extract_offences(tei_doc, file_path)
    except lxml.etree.XMLSyntaxError as err:
        error_docs[file_path] = err
        continue
    doc_id = re.match(".*?/([^/]+).xml", file_path).group(1)
    print(doc_id)

for e in events:
    e.check_4_empty_fields()

if error_docs:
    print(f"\n\n{len(error_docs)} faulty docs:")
    for doc, err in error_docs.items():
        print(f"{doc}:\t{err}")

print(f"{events_with_missing_field} of {len(events)} events are missing infos in one or more of these fields: '{', '.join(list(set(all_missing_fields)))}'")