import typing
import glob
import re
import lxml
import json
import os
from lxml import etree
from acdh_tei_pyutils.tei import TeiReader


cases_dir = "./todesurteile_master/303_annot_tei/*.xml"
error_docs = {}
all_missing_fields = []
events_with_missing_field = 0
used_ids = []
file_output = "out"
global_events_by_ids = {}
filepaths_by_fileidentifiers = {}


class DuplicatedIdError(Exception):
    pass


def check_global_id(new_glob_id):
    if new_glob_id in used_ids:
        print(f"Automatically created Id {new_glob_id} is already in use")
        raise DuplicatedIdError
    used_ids.append(new_glob_id)


class UniqueStringVals:
    def __init__(
        self,
        id_prefix: str,
        id_suffix: str,
        id_nmbr_len=2,
        default_labels=[]
    ):
        self.id_nmbr_len = id_nmbr_len
        self.counter = 0
        self.id_suffix = id_suffix
        self.id_prefix = id_prefix
        self.labels_2_ids = {}
        self.ids_2_labels = {}
        if default_labels:
            for label in default_labels:
                self.create_entry(label)

    def create_id(self):
        self.counter += 1
        return (self.id_suffix
                + str(self.counter).zfill(self.id_nmbr_len))

    def create_entry(self, label):
        new_id = self.create_id()
        self.labels_2_ids[label] = new_id
        self.ids_2_labels[new_id] = label

    def get_id_for_label(self, label: str):
        if label not in self.labels_2_ids:
            self.create_entry(label)
        return self.labels_2_ids[label]

    def to_json(self):
        return {(_id, label) for _id, label in self.ids_2_labels}


class ToolTypes(UniqueStringVals):
    def __init__(self, id_prefix: str, id_suffix: str, id_nmbr_len=2):
        super().__init__(id_prefix, id_suffix, id_nmbr_len)


class Places(UniqueStringVals):
    def __init__(self, id_prefix: str, id_suffix: str, id_nmbr_len=2):
        super().__init__(id_prefix, id_suffix, id_nmbr_len)


class OffenceTypes(UniqueStringVals):
    def __init__(self, id_prefix: str, id_suffix: str, id_nmbr_len=2):
        super().__init__(id_prefix, id_suffix, id_nmbr_len)


class MethodsOfPunishment(UniqueStringVals):
    def __init__(self, id_prefix: str, id_suffix: str, id_nmbr_len=2):
        super().__init__(id_prefix, id_suffix, id_nmbr_len)


tools_index = ToolTypes(
    id_prefix="tool",
    id_suffix="",
    id_nmbr_len=3
)

places_index = Places(
    id_prefix="place",
    id_suffix="",
    id_nmbr_len=4
)

offence_index = OffenceTypes(
    id_prefix="offence",
    id_suffix="",
    id_nmbr_len=3
)

punishment_index = MethodsOfPunishment(
    id_prefix="punishment",
    id_suffix="",
    id_nmbr_len=3
)


class Event:
    # fields that if missing seem not to indicate error
    regulary_missing_fields = [
        "tools",
        "date",
        "element",
        "place",
        "description",
        "completed",
        "aided",
        "proven_by_persecution",
        "is_probably_copy",
        "ref",
        "xml_source_id"
    ]

    xml_offence_types = [
        'offenceAttempted',
        'offence',
        'offenceSuspected',
        'offenceAided',
    ]
    xml_trial_result_types = [
        'punishment',
        'execution',
        'verdict'
    ]
    id_delim = "_"
    random_counter = 0

    def __init__(
            self,
            _type: str,
            _id: list,
            date: list,
            place: list,
            description: list,
            xml_element: etree._Element,
            file_identifier: str,
            global_id_prefix: str = "") -> None:
        self.type: str = _type if _type else ""
        if _id:
            self.id = _id[0].strip(" #")
            self.is_probably_copy = True if "#" in _id[0] else False
            self.xml_source_id = _id[0]
        else:
            Event.random_counter += 1
            self.id = f"{Event.random_counter:04}"
            self.is_probably_copy = False
            self.xml_source_id = ""
        self.date: str = date[0] if date else ""
        self.place: str = place[0] if place else ""
        self.description: str = description[0] if description else ""
        self.element: etree._Element = xml_element
        self.ref: str = xml_element.attrib.get("ref")
        self.file_identifier: str = file_identifier
        self.global_id = None
        self.global_id_prefix = global_id_prefix
        self.create_global_id()
        global_events_by_ids[self.global_id] = self

    def create_global_id(self, override=False):
        if self.global_id is not None and not override:
            raise ValueError
        new_glob_id = self.global_id_prefix + Event.id_delim + \
            self.file_identifier + Event.id_delim+self.id
        try:
            check_global_id(new_glob_id)
        except DuplicatedIdError:
            if (
                self.is_probably_copy
                or global_events_by_ids[new_glob_id].is_probably_copy
            ):
                raise DuplicatedIdError(
                    "caused by referecence, unproblematic", new_glob_id)
            else:
                raise DuplicatedIdError(
                    f"problem with {new_glob_id}", new_glob_id)
        self.global_id = new_glob_id
        return self.global_id

    def get_global_id(self):
        if self.global_id is None:
            return self.create_global_id()
        else:
            return self.global_id

    def get_source_string(self):
        return etree.tostring(
            self.element
        ).decode()

    def print_source(self):
        print(
            self.get_source_string()
        )

    def get_etree(self):
        return self.element

    def check_4_empty_fields(self):
        global all_missing_fields
        global events_with_missing_field
        missing_vals = [field for field, val in vars(self).items() if (
            field not in Event.regulary_missing_fields and not bool(val))]
        all_missing_fields += missing_vals
        if missing_vals:
            events_with_missing_field += 1
            print(f"\nmissing: {', '.join(missing_vals)}")
            print("\nsource:")
            self.print_source()

    def to_json(self):
        return {
            "id": self.get_global_id(),
            "type": self.type,
            "date": self.date,
            "place": self.place,
            "description": self.description
        }


class TrialResult(Event):
    def __init__(
            self,
            _type: str,
            _id: list,
            date: list,
            place: list,
            description: list,
            xml_element: etree._Element,
            file_identifier: str
    ):
        super().__init__(
            _type,
            _id,
            date,
            place,
            description,
            xml_element,
            file_identifier,
            "trial_result"
        )

    def to_json(self):
        json_base_dict = super().to_json()
        json_extra_dict = {"xml": self.get_source_string()}
        return json_base_dict | json_extra_dict


class Punishment(Event):
    type_key = "punishment"

    def __init__(
            self,
            _type: str,
            _id: list,
            date: list,
            place: list,
            description: list,
            xml_element: etree._Element,
            file_identifier: str,
            punishments_xml: list
    ):
        super().__init__(
            _type,
            _id,
            date,
            place,
            description,
            xml_element,
            file_identifier,
            "trial_result"
        )
        self.punishments_xml = punishments_xml if punishments_xml else []
        self.methods: list = self.get_punishment_methods()
        self.carried_out = True if self.methods else False

    def get_punishment_methods(self):
        methods = []
        counter = 0
        for punishment in self.punishments_xml:
            counter += 1
            number = int(punishment.get("n")) if punishment.get(
                "n") else counter
            label = punishment.text.strip()
            p_id = punishment_index.get_id_for_label(label)
            methods.append(
                {
                    "id": p_id,
                    "order": number,
                    "label": label
                }
            )
        return methods

    def to_json(self):
        json_base_dict = super().to_json()
        json_extra_dict = {
            "xml": self.get_source_string(),
            "methods": self.methods
        }
        return json_base_dict | json_extra_dict


class Offence(Event):
    def __init__(
            self,
            _type: str,
            _id: list,
            date: list,
            place: list,
            description: list,
            xml_element: etree._Element,
            file_identifier: str,
            offence_types: list,
            tools: list) -> None:
        super().__init__(
            _type,
            _id,
            date,
            place,
            description,
            xml_element,
            file_identifier,
            "offence"
        )
        self.proven_by_persecution: bool = None
        self.completed: typing.Optional[bool] = None
        self.aided: typing.Optional[bool] = None
        self.offence_types: list = offence_types
        self.tools: list = tools
        self.set_offence_status()

    def set_offence_status(self):
        if self.type == "offenceSuspected":
            self.proven_by_persecution = False
            self.completed = None
            self.aided = False
        elif self.type == "offenceAttempted":
            self.proven_by_persecution = True
            self.completed = False
            self.aided = False
        elif self.type == "offenceAided":
            self.proven_by_persecution = True
            self.completed = True
            self.aided = True
        elif self.type == "offence":
            self.proven_by_persecution = True
            self.completed = True
            self.aided = False
        else:
            print(f"unexpected offence type {self.type}")
            raise ValueError

    def to_json(self):
        json_base_dict = super().to_json()
        json_extra_dict = {
            "proven_by_persecution": self.proven_by_persecution,
            "completed": self.completed,
            "aided": self.aided,
            "offence_types": self.offence_types,
            "tools": self.tools
        }
        return json_base_dict | json_extra_dict


def extract_events(doc: TeiReader, file_identifier: str):
    events = []
    for event_element in doc.any_xpath(
        ".//tei:event"
    ):
        event_type: str = event_element.xpath(
            "./@type", namespaces=doc.nsmap)[0]
        xml_id: list = event_element.xpath(
            "./@xml:id", namespaces=doc.nsmap)
        if not xml_id:
            xml_id: list = event_element.xpath(
                "./@ref", namespaces=doc.nsmap
            )
            if xml_id and xml_id[0] != "#":
                xml_id = [f"#{xml_id[0]}"]
        date: list = event_element.xpath(
            "./tei:desc/tei:date/@when", namespaces=doc.nsmap)
        place: list = event_element.xpath(
            "./tei:desc/tei:placeName/text()[1]", namespaces=doc.nsmap)
        description_str: list = event_element.xpath(
            "./tei:desc/tei:desc/text()", namespaces=doc.nsmap)
        event_obj = None
        if event_type in Event.xml_offence_types:
            try:
                typed_offences: list = event_element.xpath(
                    '''./tei:desc/tei:trait[@type='typeOfOffence']/
                    tei:desc/tei:list/tei:item/text()''',
                    namespaces=doc.nsmap
                )
                typed_tools: list = event_element.xpath(
                    '''./tei:desc/tei:trait[@type='toolOfCrime']
                    /tei:desc/text()''',
                    namespaces=doc.nsmap
                )
                event_obj = Offence(
                    _type=event_type,
                    _id=xml_id,
                    date=date,
                    place=place,
                    description=description_str,
                    xml_element=event_element,
                    file_identifier=file_identifier,
                    offence_types=typed_offences,
                    tools=typed_tools,
                )
            except DuplicatedIdError as e:
                if "unproblematic" in e.args[0]:
                    # existing_event_id = e.args[1]
                    # this id can later be used for referencing
                    pass
                else:
                    raise e
        elif event_type in Event.xml_trial_result_types:
            try:
                if event_type == Punishment.type_key:
                    punishments_xml = event_element.xpath(
                        ".//tei:desc/tei:list/tei:item",
                        namespaces=doc.nsmap
                    )
                    if not (punishments_xml):
                        punishments_xml = event_element.xpath(
                            ".//tei:desc//tei:desc",
                            namespaces=doc.nsmap
                        )
                    event_obj = Punishment(
                        _type=event_type,
                        _id="",  # ids not necessary there
                        date=date,
                        place=place,
                        description=description_str,
                        xml_element=event_element,
                        file_identifier=file_identifier,
                        punishments_xml=punishments_xml
                    )
                else:
                    event_obj = TrialResult(
                        _type=event_type,
                        _id="",  # ids not necessary there
                        date=date,
                        place=place,
                        description=description_str,
                        xml_element=event_element,
                        file_identifier=file_identifier
                    )
            except DuplicatedIdError as e:
                if "unproblematic" in e.args[0]:
                    pass
                else:
                    raise e
        if event_obj:
            events.append(event_obj)
    return events


def extract_offences(doc: TeiReader, file_identifier: str):
    events = []
    for event_element in doc.any_xpath(
        ".//tei:listEvent[@type='offences']/tei:event"
    ):
        event_type: str = event_element.xpath(
            "./@type", namespaces=doc.nsmap)[0]
        # if more then 1 person is associtated with the event
        # it just gets referenced, while data are doublicated (?)
        xml_id: list = event_element.xpath(
            "./@xml:id|./@ref", namespaces=doc.nsmap)
        # desc cant contain:
        # desc', 'ref', 'trait', 'placeName', 'date'
        date: list = event_element.xpath(
            "./tei:desc/tei:date/@when", namespaces=doc.nsmap)
        place: list = event_element.xpath(
            "./tei:desc/tei:placeName/text()[1]", namespaces=doc.nsmap)
        description_str: list = event_element.xpath(
            "./tei:desc/tei:desc/text()[1]", namespaces=doc.nsmap)
        typed_offences: list = event_element.xpath(
            '''./tei:desc/tei:trait[@type='typeOfOffence']/
            tei:desc/tei:list/tei:item/text()''',
            namespaces=doc.nsmap
        )
        typed_tools: list = event_element.xpath(
            '''./tei:desc/tei:trait[@type='toolOfCrime']
            /tei:desc/text()''',
            namespaces=doc.nsmap)
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
        filepaths_by_fileidentifiers[file_identifier] = file_path
        print(file_path)
        try:
            tei_doc = TeiReader(file_path)
            # events += extract_offences(tei_doc, file_identifier)
            events += extract_events(tei_doc, file_identifier)
        except lxml.etree.XMLSyntaxError as err:
            error_docs[file_path] = err
            continue
        doc_id = re.match(".*?/([^/]+).xml", file_path).group(1)

    for e in events:
        e.check_4_empty_fields()
        events_json[e.get_global_id()] = e.to_json()
        listevent.append(e.get_etree())

    if error_docs:
        print(f"\n\n{len(error_docs)} faulty docs:")
        for doc, err in error_docs.items():
            print(f"{doc}:\t{err}")

    os.makedirs(file_output, exist_ok=True)
    template_doc.tree_to_file(f"{file_output}/offences.xml")
    with open(f"{file_output}/offences.json", "w") as f:
        json.dump(events_json, f, indent=4)
    missing_fields = ', '.join(list(set(all_missing_fields)))
    if events_with_missing_field:
        logmessage = (
            f"{events_with_missing_field} of {len(events)} events are "
            f"missing infos in one or more of these fields: '{missing_fields}'"
        )
        print(logmessage)
