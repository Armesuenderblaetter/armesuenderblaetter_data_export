import typing
import glob
import re
import lxml
import json
import os
from lxml import etree
from acdh_tei_pyutils.tei import TeiReader
from acdh_tei_pyutils.utils import extract_fulltext
from copy import deepcopy


cases_dir = "./todesurteile_master/303_annot_tei/*.xml"
error_docs = {}
all_missing_fields = []
events_with_missing_field = 0
used_ids = []
file_output = "out"
global_events_by_ids = {}


class DuplicatedIdError(Exception):
    pass


def check_global_id(new_glob_id):
    if new_glob_id in used_ids:
        print(f"Automatically created Id {new_glob_id} is already in use")
        raise DuplicatedIdError
    used_ids.append(new_glob_id)


class UniqueStringVals:
    spacer = "_"

    def __init__(
        self,
        id_prefix: str,
        id_suffix: str,
        id_nmbr_len=2,
        default_labels=[]
    ):
        self.id_nmbr_len = id_nmbr_len
        self.counter = 0
        self.id_suffix = (UniqueStringVals.spacer
                          + id_suffix if id_suffix else "")
        self.id_prefix = id_prefix
        self.labels_2_ids = {}
        self.ids_2_labels = {}
        if default_labels:
            for label in default_labels:
                self.create_entry(label)

    def create_id(self):
        self.counter += 1
        return (self.id_prefix
                + UniqueStringVals.spacer
                + str(self.counter).zfill(self.id_nmbr_len)
                + self.id_suffix
                )

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
    id_prefix="tool_type",
    id_suffix="",
    id_nmbr_len=3
)

places_index = Places(
    id_prefix="place",
    id_suffix="",
    id_nmbr_len=4
)

offence_index = OffenceTypes(
    id_prefix="offence_type",
    id_suffix="",
    id_nmbr_len=3
)

punishment_index = MethodsOfPunishment(
    id_prefix="punishment_type",
    id_suffix="",
    id_nmbr_len=3
)

typed_indices = [tools_index, places_index, offence_index, punishment_index]


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
        "xml_source_id",
        "places"
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
        self.date: str = date if date else ""
        self.places: list = self.get_places(place)
        self.description: str = "".join(
            [re.sub(" +", " ", desc) for desc in description])
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
        return deepcopy(self.element)

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

    def get_places(self, places):
        unique_places = []
        for place in places:
            label = place.strip()
            p_id = places_index.get_id_for_label(label)
            unique_places.append(
                {
                    "id": p_id,
                    "label": label
                }
            )
        return unique_places

    def to_json(self):
        return {
            "id": self.get_global_id(),
            "type": self.type,
            "date": self.date,
            "place": self.places,
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


class Execution(Event):
    type_key = "execution"

    def __init__(
            self,
            _type: str,
            _id: list,
            date: list,
            place: list,
            description: list,
            xml_element: etree._Element,
            file_identifier: str,
            methods_xml: list
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
        self.methods_xml = methods_xml if methods_xml else []
        self.methods: list = self.get_execution_methods()
        self.carried_out = True if self.methods else False

    def get_execution_methods(self):
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


class Person:
    global_id_prefix = "pers"
    delim = "_"
    random_counter = 0

    def __init__(
        self,
        xml_id: str,
        roles: dict,
        forename: str,
        surname: str,
        birth_element: etree._Element,
        death_element: etree._Element,
        sex: str,
        age: str,
        _type: str,
        marriage_status: str,
        faith: str,
        occupation: str,
        file_identifier: str,
        xml_element: etree._Element
    ):
        # what about role?
        self.xml_id: str = xml_id
        self.id = xml_id if xml_id else ""
        if not self.id:
            Person.random_counter += 1
            self.id = f"{Person.random_counter:04}"
        self.roles: dict = dict(
            [(file_identifier, role) for role in roles]
        )
        self.forename: str = forename
        self.surname: str = surname
        self.birth_element: etree._Element = (birth_element[0]
                                              if birth_element else None)
        self.death_element: etree._Element = (death_element[0]
                                              if death_element else None)
        self.sex: str = sex
        self.age: str = age
        self.type: str = _type
        self.marriage_status: str = marriage_status
        self.faith: str = faith
        self.occupation: str = occupation
        self.global_id = None
        self.file_identifier = file_identifier
        self.related_events = []
        self.element: etree._Element = xml_element

    def create_global_id(self, override=False):
        if self.global_id is not None and not override:
            raise ValueError("logic error somewhere!", self.global_id)
        new_glob_id = Person.global_id_prefix + Person.delim + \
            self.file_identifier + Person.delim+self.id
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

    def append_related_event(self, event):
        self.related_events.append(event)

    def get_etree(self):
        return deepcopy(self.element)

    def get_source_string(self):
        return etree.tostring(
            self.element
        ).decode()

    def to_json(self):
        return {
            "global_id": self.global_id,
            "forename": self.forename,
            "surname": self.surname,
            "birth_element": etree.tostring(
                self.birth_element
            ).decode() if self.birth_element is not None else "",
            "death_element": etree.tostring(
                self.death_element
            ).decode() if self.death_element is not None else "",
            "roles": self.roles,
            "sex": self.sex,
            "age": self.age,
            "type": self.type,
            "marriage_status": self.marriage_status,
            "faith": self.faith,
            "occupation": self.occupation,
            "file_identifier": self.file_identifier,
            "related_events": [
                event.get_global_id() for event in self.related_events
            ],
            "element": self.get_source_string()
        }


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
        self.offence_types: list = []
        self.get_offence_types(offence_types)
        self.tools: list = []
        self.get_typed_tools(tools)
        self.set_offence_status()

    def get_typed_tools(self, raw_tools):
        counter = 0
        processed_tools = []
        for t in raw_tools:
            if t.strip():
                if "," in t:
                    ts = t.split(",")
                    for sub_t in ts:
                        if sub_t.strip():
                            processed_tools.append(sub_t)
                else:
                    processed_tools.append(t)

        for label in processed_tools:
            counter += 1
            tool_id = tools_index.get_id_for_label(label)
            self.tools.append(
                {
                    "id": tool_id,
                    "order": counter,
                    "label": label
                }
            )

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

    def get_offence_types(self, offences: list):
        counter = 0
        for offence in offences:
            counter += 1
            offence_id = offence_index.get_id_for_label(offence.strip())
            self.offence_types.append(
                {
                    "id": offence_id,
                    "order": counter,
                    "label": offence
                }
            )


def extract_person(
        person_element: etree._Element,
        file_identifier: str, nsmap: dict
) -> Person:
    xml_id = person_element.xpath("@xml:id", namespaces=nsmap)
    roles = person_element.xpath("@role", namespaces=nsmap)
    forename = person_element.xpath(
        "./tei:persName/tei:forename/text()", namespaces=nsmap)
    surename = person_element.xpath(
        "./tei:persName/tei:surname//text()[normalize-space(.)!='']",
        namespaces=nsmap
    )
    birth_element = person_element.xpath("./tei:birth", namespaces=nsmap)
    death_element = person_element.xpath("./tei:death", namespaces=nsmap)
    sex = person_element.xpath("./tei:sex/@value", namespaces=nsmap)
    # age = person_element.xpath("./tei:age/@value", namespaces=nsmap)
    age = person_element.xpath("./tei:age/text()", namespaces=nsmap)
    _type = person_element.xpath("./tei:state/@type", namespaces=nsmap)
    marriage_state = person_element.xpath(
        "./tei:state/tei:desc//text()", namespaces=nsmap)[0]
    faith = person_element.xpath("./tei:faith/text()", namespaces=nsmap)[0]
    occupation = person_element.xpath(
        "./tei:occupation/text()", namespaces=nsmap)
    person_obj = Person(
        xml_id=xml_id[0] if xml_id else "",
        roles=roles,
        forename=forename[0] if forename else "",
        surname=surename[0] if surename else "",
        birth_element=birth_element,
        death_element=death_element,
        sex=sex[0] if sex else "",
        age=age[0] if age else "",
        _type=_type[0] if _type else "",
        marriage_status=marriage_state,
        faith=faith,
        occupation=occupation,
        file_identifier=file_identifier,
        xml_element=person_element
    )
    try:
        person_obj.create_global_id()
    except ValueError as e:
        input(e)
    return person_obj


def extract_event(
    event_element: etree._Element,
    file_identifier: str,
    nsmap: dict
):
    event_type: str = event_element.xpath(
        "./@type", namespaces=nsmap)[0]
    xml_id: list = event_element.xpath(
        "./@xml:id", namespaces=nsmap)
    if not xml_id:
        xml_id: list = event_element.xpath(
            "./@ref", namespaces=nsmap
        )
        if xml_id and xml_id[0] != "#":
            xml_id = [f"#{xml_id[0]}"]
    dates: list = []
    date: list = event_element.xpath(
        "./tei:desc/tei:date", namespaces=nsmap)
    if len(date) == 2:
        print(f"multiple dates in {xml_id}")
        date1, date2 = event_element.xpath(
            "./tei:desc/tei:date", namespaces=nsmap)
        try:
            date1_when = date1.attrib["when"]
            dates.append(date1_when)
        except KeyError:
            date1_when = " ".join(date1.xpath(".//text()", namespaces=nsmap))
            dates.append(re.sub(r"\s+", " ", date1_when).strip())
            try:
                date_exec = date1.xpath(
                    """ancestor::tei:person/tei:event[@type='execution']
                    /tei:desc/tei:date/@when""",
                    namespaces=nsmap)[0]
                dates.append(date_exec)
            except IndexError:
                try:
                    date_exec = date1.xpath(
                        """ancestor::tei:person/tei:event[@type='verdict']
                        /tei:desc/tei:date/@when""",
                        namespaces=nsmap)[0]
                    dates.append(date_exec)
                except IndexError:
                    date_exec = ""
                    dates.append(date_exec)
        try:
            date2_when = date2.attrib["when"]
            dates.append(date2_when)
        except KeyError:
            date2_when = " ".join(date2.xpath(".//text()", namespaces=nsmap))
            dates.append(re.sub(r"\s+", " ", date2_when).strip())
    elif len(date) == 1:
        try:
            date_when = date[0].attrib["when"]
            dates.append(date_when)
        except KeyError:
            date_when = " ".join(date[0].xpath(".//text()", namespaces=nsmap))
            if "before" in date_when:
                dates.append(re.sub(r"\s+", " ", date_when).strip())
            try:
                date_exec = date[0].xpath(
                    """ancestor::tei:person/tei:event[@type='execution']
                    /tei:desc/tei:date/@when""",
                    namespaces=nsmap)[0]
                dates.append(date_exec)
            except IndexError:
                try:
                    date_exec = date[0].xpath(
                        """ancestor::tei:person/tei:event[@type='verdict']
                        /tei:desc/tei:date/@when""",
                        namespaces=nsmap)[0]
                    dates.append(date_exec)
                except IndexError:
                    date_exec = ""
                    dates.append(date_exec)
            if "after" in date_when:
                dates.append(re.sub(r"\s+", " ", date_when).strip())
    else:
        print("no date or more than two dates in ", xml_id)
    place: list = event_element.xpath(
        "./tei:desc/tei:placeName/text()[1]", namespaces=nsmap)
    description_str: list = event_element.xpath(
        "./tei:desc/tei:desc//text()", namespaces=nsmap)
    event_obj = None
    if event_type in Event.xml_offence_types:
        try:
            typed_offences: list = event_element.xpath(
                '''./tei:desc/tei:trait[@type='typeOfOffence']/
                tei:desc/tei:list/tei:item/text()''',
                namespaces=nsmap
            )
            typed_tools: list = event_element.xpath(
                '''./tei:desc/tei:trait[@type='toolOfCrime']
                /tei:desc//text()''',
                namespaces=nsmap
            )
            event_obj = Offence(
                _type=event_type,
                _id=xml_id,
                date=dates,
                place=place,
                description=description_str,
                xml_element=event_element,
                file_identifier=file_identifier,
                offence_types=typed_offences,
                tools=typed_tools,
            )
        except DuplicatedIdError as e:
            if "unproblematic" in e.args[0]:
                existing_event_id = e.args[1]
                return existing_event_id
            else:
                raise e
    elif event_type in Event.xml_trial_result_types:
        try:
            if event_type == Punishment.type_key:
                punishments_xml = event_element.xpath(
                    ".//tei:desc/tei:list/tei:item",
                    namespaces=nsmap
                )
                if not (punishments_xml):
                    punishments_xml = event_element.xpath(
                        ".//tei:desc//tei:desc",
                        namespaces=nsmap
                    )
                event_obj = Punishment(
                    _type=event_type,
                    _id="",  # ids not necessary there
                    date=dates,
                    place=place,
                    description=description_str,
                    xml_element=event_element,
                    file_identifier=file_identifier,
                    punishments_xml=punishments_xml
                )
            elif event_type == Execution.type_key:
                punishments_xml = event_element.xpath(
                    ".//tei:desc/tei:list/tei:item",
                    namespaces=nsmap
                )
                if not (punishments_xml):
                    punishments_xml = event_element.xpath(
                        ".//tei:desc//tei:desc",
                        namespaces=nsmap
                    )
                event_obj = Punishment(
                    _type=event_type,
                    _id="",  # ids not necessary there
                    date=dates,
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
                    date=dates,
                    place=place,
                    description=description_str,
                    xml_element=event_element,
                    file_identifier=file_identifier
                )
        except DuplicatedIdError as e:
            if "unproblematic" in e.args[0]:
                return e.args[1]
            else:
                raise e
    return event_obj


def extract_events_and_persons(doc: TeiReader, file_identifier: str):
    events = []
    persons = []
    for person_element in doc.any_xpath("//tei:person"):
        person_obj: Person = extract_person(
            person_element, file_identifier, doc.nsmap)
        persons.append(person_obj)
        for event_element in person_element.xpath(
            ".//tei:event",
            namespaces=doc.nsmap
        ):
            event_obj = extract_event(
                event_element,
                file_identifier,
                doc.nsmap
            )
            if event_obj:
                if isinstance(event_obj, str):
                    person_obj.append_related_event(
                        global_events_by_ids[event_obj]
                    )
                else:
                    events.append(event_obj)
                    person_obj.append_related_event(event_obj)
    return events, persons


def print_to_json(objects, category):
    object_json = dict((obj.get_global_id(), obj.to_json()) for obj in objects)
    fp = f"{file_output}/{category}.json"
    with open(fp, "w") as f:
        print(f"writing to {fp}")
        json.dump(object_json, f, indent=4)


def print_indices_to_json():
    for index in typed_indices:
        with open(f"{file_output}/unique_{index.id_prefix}.json", "w") as f:
            json.dump(index.ids_2_labels, f, indent=4)


def prepare_output_folder():
    old_files = glob.glob(f"./{file_output}/*.json")
    for old_file in old_files:
        os.remove(old_file)
    os.makedirs(file_output, exist_ok=True)

class XmlDocument:
    def __init__(
            self,
            xml_tree: TeiReader,
            path:str,
            identifier:str, 
            events:list,
            persons: list
    ):  
        self.xml_tree: TeiReader = xml_tree
        self.path: str = path
        print(self.path)
        self.id: str = identifier
        self.global_id = None
        self.events: list = events
        self.persons: list = persons
        self.fulltext: str = extract_fulltext(
            self.xml_tree.any_xpath("//tei:text")[0],
            tag_blacklist=[
                "{http://www.tei-c.org/ns/1.0}fs",
                "{http://www.tei-c.org/ns/1.0}f"
            ]
        )
        self.title: str = extract_fulltext(
            self.xml_tree.any_xpath("//tei:title")[0],
            tag_blacklist=[
                "{http://www.tei-c.org/ns/1.0}fs",
                "{http://www.tei-c.org/ns/1.0}f"
            ]
        )

    def get_global_id(self):
        if self.global_id is None:
            try:
                check_global_id(self.id)
            except:
                input(f"Document id '{self.id}' used more then once.")
                raise ValueError
            self.global_id = self.id
        return self.global_id

    def to_json(self):
        persons = [p.get_global_id() for p in self.persons]
        events = [e.get_global_id() for e in self.events]
        return {
            "title" : self.title,
            "id" : self.get_global_id(),
            "local_path" : self.path,
            "contains_persons" : persons,
            "contains_events" : events,
            "fulltext": self.fulltext
        }


if __name__ == "__main__":
    event_objs = []
    person_objs = []
    events_json = {}
    xml_docs = []
    template_doc = TeiReader("template/events.xml")
    listevent = template_doc.any_xpath(".//tei:listEvent[@type='offences']")[0]
    for file_path in glob.glob(cases_dir):
        #file_identifier = file_path.split("/")[-1]
        doc_id = re.match(".*?/([^/]+).xml", file_path).group(1)
        print(file_path)
        try:
            tei_doc = TeiReader(file_path)
            entitie_objects = extract_events_and_persons(
                tei_doc,
                doc_id
            )
            event_objs += entitie_objects[0]
            person_objs += entitie_objects[1]
            xml_doc = XmlDocument(
                tei_doc,
                file_path,
                doc_id,
                entitie_objects[0],
                entitie_objects[1],
            )
            xml_docs.append(xml_doc)
        except lxml.etree.XMLSyntaxError as err:
            error_docs[file_path] = err
            continue

    punishment_objects = []
    offences_objects = []
    for event in event_objs:
        event.check_4_empty_fields()
        if isinstance(event, Offence):
            offences_objects.append(event)
        else:
            punishment_objects.append(event)
        listevent.append(event.get_etree())

    prepare_output_folder()
    template_doc.tree_to_file(f"{file_output}/events.xml")
    print_to_json(offences_objects, "offences")
    print_to_json(punishment_objects, "punishments")
    print_to_json(person_objs, "persons")
    print_to_json(xml_docs, "documents")
    missing_fields = ', '.join(list(set(all_missing_fields)))
    if events_with_missing_field:
        logmessage = (
            f"{events_with_missing_field} of {len(event_objs)} events are "
            f"missing infos in one or more of these fields: '{missing_fields}'"
        )
        print(logmessage)

    if error_docs:
        print(f"\n\n{len(error_docs)} faulty docs:")
        for doc, err in error_docs.items():
            print(f"{doc}:\t{err}")

    print_indices_to_json()
