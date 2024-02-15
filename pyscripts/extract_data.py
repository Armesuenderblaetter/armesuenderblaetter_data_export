import typing
import glob
import re
import lxml
import json
import os
from lxml import etree
from acdh_tei_pyutils.tei import TeiReader
from acdh_baserow_pyutils import BaseRowClient
cases_dir = "./todesurteile_master/303_annot_tei/*.xml"
error_docs = {}

all_missing_fields = []
events_with_missing_field = 0
used_ids = []
file_output = "out"


class DuplicatedIdError(Exception):
    pass

def check_global_id(new_glob_id):
    if new_glob_id in used_ids:
        print(f"Automatically created Id {new_glob_id} is already in use")
        raise DuplicatedIdError
    used_ids.append(new_glob_id)

class UniqueStringVals:
    def __init__(self, id_prefix:str, id_suffix:str, id_nmbr_len=2, default_labels=[]):
        self.id_nmbr_len = id_nmbr_len
        self.counter = 0
        self.id_suffix= id_suffix
        self.id_prefix = id_prefix
        self.labels_2_ids = {}
        self.ids_2_labels = {}
        if default_labels:
            for label in default_labels:
                self.create_entry(label)

    def create_id(self):
        self.counter += 1
        return f"{self.id_suffix}{self.counter:0>self.id_nmbr_len}"

    def create_entry(self, label):
        new_id = self.create_id()
        self.labels_2_ids[label] = new_id
        self.ids_2_labels[new_id] = label

    def get_id_for_label(self, label:str):
        if not label in self.labels_2_ids:
            self.create_entry(label)
        return self.labels_2_ids[label]


class ToolTypes(UniqueStringVals):
    def __init__(self, id_prefix: str, id_suffix: str, id_nmbr_len=2):
        super().__init__(id_prefix, id_suffix, id_nmbr_len)

class Places(UniqueStringVals):
    def __init__(self, id_prefix: str, id_suffix: str, id_nmbr_len=2):
        super().__init__(id_prefix, id_suffix, id_nmbr_len)

class OffenceTypes(UniqueStringVals):
    def __init__(self, id_prefix: str, id_suffix: str, id_nmbr_len=2):
        super().__init__(id_prefix, id_suffix, id_nmbr_len)

class Event:
    regulary_missing_fields = [
        "tools",
        "date",
        "element",
        "place",
        "description",
        "completed",
        "aided",
        "proven_by_persecution"
    ]
    id_delim = "_"
    def __init__(
            self,
            _type:list,
            _id:list,
            date:list,
            place:list,
            description:list,
            xml_element: etree._Element,
            file_identifier:str) -> None:
        self.type: str = _type[0] if _type else ""
        self.id: str = _id[0].strip(" #") if _id else ""
        self.date: str = date[0] if date else ""
        self.place: str = place[0] if place else ""
        self.description: str = description[0] if description else ""
        self.element: etree._Element = xml_element
        self.file_identifier: str = file_identifier
        self.global_id = None
        self.global_id_prefix = ""

    def create_global_id(self):
        new_glob_id = self.global_id_prefix + Event.id_delim + self.file_identifier + Event.id_delim+self.id
        check_global_id(new_glob_id)
        self.global_id = new_glob_id
        return self.global_id

    def get_global_id(self):
        if self.global_id is None:
            return self.create_global_id()
        else:
            return self.global_id

    def print_source(self):
        print(
            etree.tostring(
                self.element
            ).decode()
        )

    def get_etree(self):
        return self.element

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


class Offence(Event):
    def __init__(
            self,
            _type:list,
            _id:list,
            date:list,
            place:list,
            description:list,
            xml_element: etree._Element,
            file_identifier:str,
            offence_types:list,
            tools:list ) -> None:
        Event.__init__(self, _type, _id, date, place, description, xml_element, file_identifier)
        self.proven_by_persecution: bool = None
        self.completed: typing.Optional[bool]=None
        self.aided: typing.Optional[bool]=None
        self.offence_types: list = offence_types
        self.tools: list = tools
        self.global_id_prefix = "offence"
        self.set_offence_status()
        self.create_global_id()

    def set_offence_status(self):
        if self.type == "offenceSuspected":
            self.proven_by_persecution = False
            self.completed = None
            self.aided = False
        if self.type == "offenceAttempted":
            self.proven_by_persecution = True
            self.completed = False
            self.aided = False
        if self.type == "offenceAided":
            self.proven_by_persecution = True
            self.completed = True
            self.aided = True

    def parse_json(self):
        return {
            "id": self.get_global_id(),
            "type": self.type,
            "date": self.date,
            "place": self.place,
            "description": self.description,
            "proven_by_persecution": self.proven_by_persecution,
            "completed": self.completed,
            "aided": self.aided,
            "offence_types": self.offence_types,
            "tools": self.tools
        }


def extract_offences(doc:TeiReader, file_identifier: str):
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
        try:
            offence = Offence(
                event_type,
                xml_id,
                date,
                place,
                description_str,
                event_element,
                file_identifier,
                typed_offences,
                typed_tools
            )
            events.append(offence)
        except DuplicatedIdError:
            # this can happen since some of the offences where commited by more then one person and get referenced/duplicated in the docs
            pass
    return events


if __name__ == "__main__":
    events = []
    events_json = {}
    template_doc = TeiReader("template/events.xml")
    listevent = template_doc.any_xpath(".//tei:listEvent[@type='offences']")[0]
    counter = 0
    for file_path in glob.glob(cases_dir):
        counter += 1
        file_identifier = str(counter).zfill(5)
        print(file_path)
        try:
            tei_doc = TeiReader(file_path)
            events += extract_offences(tei_doc, file_identifier)
        except lxml.etree.XMLSyntaxError as err:
            error_docs[file_path] = err
            continue
        doc_id = re.match(".*?/([^/]+).xml", file_path).group(1)

    for e in events:
        e.check_4_empty_fields()
        events_json[e.get_global_id()] = e.parse_json()
        listevent.append(e.get_etree())

    if error_docs:
        print(f"\n\n{len(error_docs)} faulty docs:")
        for doc, err in error_docs.items():
            print(f"{doc}:\t{err}")

    os.makedirs(file_output, exist_ok=True)
    template_doc.tree_to_file(f"{file_output}/offences.xml")
    with open(f"{file_output}/offences.json", "w") as f:
        json.dump(events_json, f, indent=4)
    print(f"{events_with_missing_field} of {len(events)} events are missing infos in one or more of these fields: '{', '.join(list(set(all_missing_fields)))}'")
