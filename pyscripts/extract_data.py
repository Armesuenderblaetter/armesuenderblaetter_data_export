#!/usr/bin/env python
import typing
import glob
import re
import lxml
import json
import os
from pathlib import Path
import lxml.etree as etree
import lxml.builder as builder
from copy import deepcopy
from acdh_tei_pyutils.tei import TeiReader
from acdh_tei_pyutils.utils import extract_fulltext

# import mk_verticals
from label_translator import label_dict
from tidy_rdgs import tidy_readings

xmlns = "http://www.w3.org/XML/1998/namespace"


punishments_dict = {
    "bodies on wheel": "Rad (Körper)",
    "body on wheel": "Rad (Körper)",
    "burned": "Verbrennung",
    "hand chopped": "Handabhauung",
    "head on pale": "Pfahl (Kopf)",
    "heads on pale": "Pfahl (Kopf)",
    "pale": "Pfahl",
    "pale (head)": "Pfahl (Kopf)",
    "right hand chopped": "Handabhauung (rechte Hand)",
    "quartered": "Vierteilung",
    "shot": "Erschießung",
    "stack": "Gesteck (Kopf)",
    "stake": "Gesteck (Kopf)",
    "strand": "Strang",
    "sword": "Schwert",
    "wheel": "Rad",
    "30 Jahre Gefängnis zweiten Grades": "Gefängnis zweiten Grades",
    "wheel (body)": "Rad (Körper)",
    "wheel from above": "Rad von oben",
    "wheel from above (begnadigt)": "Rad von oben (begnadigt)",
    "wheel from beneath": "Rad von unten",
    "wheel from beyond": "Rad von hinten",
    "Zwicken mit glühenden Zangen in die rechte Brust": "glühende Zangen (rechte Brust)",
    "dreimaliger Zwick mit glühenden Zangen an verschiedenen Orten": "glühende Zangen (x3)",
    "Brandmarkung durch den Freymann": "Brandmarkung",
    "zweimaliger Zwick mit glühenden Zangen": "glühende Zangen (x2)",
    "Zwick mit glühenden Zangen in die linke Brust": "glühende Zangen (linke Brust)",
    "Theile herumgetragen und seitlich an Galgen aufgenagelt": "Teile herumgetragen und an Galgen aufgenagelt",
    "StrangUrteil vollzogen; dannenhero dessen Bildnuß"
    "an die gewöhnliche Richtstatt vor "
    "das Schotten=Thor auf dasig so genannten Rabenstein ausgeführet /"
    " und an einem daselbst "
    "zu diesem Ende aufgerichteten Schnell=Galgen aufgehangen / und alda drey Tag"
    " lang hangend gelassen werden solle.": "Erhängen",
    "Teile an den Tatorten ausgestellt": "Ausstellung der Teile am Tatort",
    "Delinquent an dem Ort der begangenen Morde zeigen": "Ausstellung am Tatort",
    "Schleifen auf Kuhhaut zur Richtstatt": "Schleifen auf Kuhhaut",
    "Riemen auf der rechten Seiten aus dem Rücken schneiden": "Riemen aus dem Rücken schneiden"
}

punishments_dict_ts = {
    "Rad (Körper)": "Rad",
    "Pfahl (Kopf)": "Pfahl",
    "Handabhauung (rechte Hand)": "Handabhauung",
    "Gesteck (Kopf)": "Gesteck",
    "Rad von oben": "Rad",
    "Rad von oben (begnadigt)": "Rad",
    "glühende Zangen (rechte Brust)": "Zangen",
    "glühende Zangen (x3)": "Zangen",
    "glühende Zangen (x2)": "Zangen",
    "glühende Zangen (linke Brust)": "Zangen",
    "Ausstellung der Teile am Tatort": "Ausstellung am Tatort",
    "Brandmarkung der Wangen": "Brandmarkung",
    "Schleifen auf Kuhhaut zur Richtstatt": "Schleifen auf Kuhhaut",
    "unter dem Galgen begraben": "Verscharrung ",
    "Riemen aus dem Rücken schneiden": "Riemenschneiden",
    "Belegung mit schweren Eisen": "Schwere Eisen",
    "Abstrafung mit 50 Stockstreichen an jedem Jahrestage seines Vergehens": "Stockstreichen",
    "Eingeweide aus Körper gerissen": "Ausweidung",
    "Leib darunter eingescharrt": "Verscharrung ",
    "Gefängnis zweiten Grades": "Gefängnis"
}

publishers_dict = {
    "zu finden im grossen Jakoberhof Nro. 837.": "k. A.",
    "Andreas Heyinger / Acad. Buchdr.": "Andreas Heyinger",
    "J. M. Weimar": "k. A.",
    "gedruckt mit Jahnischen Schriften": "k. A."}

places_dict = {
    "Wien in Österreich": "Wien"
}

tei_nsmp = {"tei": "http://www.tei-c.org/ns/1.0", "xml": xmlns}

# # xml factory
teiMaker = builder.ElementMaker(namespace="http://www.tei-c.org/ns/1.0", nsmap=tei_nsmp)

cases_dir = "./asb_master/303_annot_tei/*.xml"
error_docs = {}
all_missing_fields = []
events_with_missing_field = 0
used_ids = []
json_file_output = "out/json"
xml_file_output = "out/xml"
xml_index_output = f"{xml_file_output}/indices"
xml_editions_output = f"{xml_file_output}/editions"
Path(f"./{json_file_output}").mkdir(parents=True, exist_ok=True)
Path(f"./{xml_index_output}").mkdir(parents=True, exist_ok=True)
Path(f"./{xml_editions_output}").mkdir(parents=True, exist_ok=True)
global_events_by_ids = {}


class DuplicatedIdError(Exception):
    pass


def clear_kA(string):
    return re.sub(r"k\. ?A\.,?", "", string).strip()


def check_global_id(new_glob_id):
    if new_glob_id in used_ids:
        print(f"Automatically created Id {new_glob_id} is already in use")
        raise DuplicatedIdError
    used_ids.append(new_glob_id)


class UniqueStringVals:
    spacer = "_"

    def __init__(
        self, id_prefix: str, id_suffix: str, id_nmbr_len=2, default_labels=[]
    ):
        self.id_nmbr_len = id_nmbr_len
        self.counter = 0
        self.id_suffix = UniqueStringVals.spacer + id_suffix if id_suffix else ""
        self.id_prefix = id_prefix
        self.labels_2_ids = {}
        self.ids_2_labels = {}
        if default_labels:
            for label in default_labels:
                self.create_entry(label)

    def create_id(self):
        self.counter += 1
        return (
            self.id_prefix
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


class MethodsOfExecution(UniqueStringVals):
    def __init__(self, id_prefix: str, id_suffix: str, id_nmbr_len=2):
        super().__init__(id_prefix, id_suffix, id_nmbr_len)


tools_index = ToolTypes(id_prefix="tool_type", id_suffix="", id_nmbr_len=3)

places_index = Places(id_prefix="place", id_suffix="", id_nmbr_len=4)

offence_index = OffenceTypes(id_prefix="offence_type", id_suffix="", id_nmbr_len=3)

punishment_index = MethodsOfPunishment(
    id_prefix="punishment_type", id_suffix="", id_nmbr_len=3
)

execution_index = MethodsOfExecution(
    id_prefix="execution_type", id_suffix="", id_nmbr_len=3
)

typed_indices = [
    tools_index,
    places_index,
    offence_index,
    punishment_index,
    execution_index,
]


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
        "rs",
        "xml_source_id",
        "places",
        "element_copies",
    ]

    xml_offence_types = [
        "offenceAttempted",
        "offence",
        "offenceSuspected",
        "offenceAided",
    ]
    xml_trial_result_types = ["punishment", "execution", "verdict"]
    id_delim = "_"
    random_counter = 0

    def __init__(
        self,
        _type: str,
        _id: list,
        date: str,
        place: list,
        description: list,
        xml_element: etree._Element,
        file_identifier: str,
        global_id_prefix: str = "",
    ) -> None:
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
            [re.sub(" +", " ", desc) for desc in description]
        )
        self.element: etree._Element = xml_element
        self.element_copies = []
        self.ref: str = xml_element.attrib.get("ref")
        self.file_identifier: str = file_identifier
        self.global_id = None
        self.global_id_prefix = global_id_prefix
        self.create_global_id()
        global_events_by_ids[self.global_id] = self
        self.rs = None
        # self.element_cp = deepcopy(self.element)

    def to_xml(self):
        self.element.set(f"{{{xmlns}}}id", self.global_id)
        return self.element

    def add_selfref_as_next(self):
        if self.rs is None:
            self.rs = teiMaker.rs(self.type, type=self.type, ref="#" + self.global_id)
            self.element.addnext(self.rs)
        if self.element_copies:
            for element in self.element_copies:
                element.addnext(deepcopy(self.rs))
                parent = element.getparent()
                parent.remove(element)
            self.element_copies = []

    def create_global_id(self, override=False):
        if self.global_id is not None and not override:
            raise ValueError
        new_glob_id = (
            self.global_id_prefix
            + Event.id_delim
            + self.file_identifier
            + Event.id_delim
            + self.id
        )
        try:
            check_global_id(new_glob_id)
        except DuplicatedIdError:
            if (
                self.is_probably_copy
                or global_events_by_ids[new_glob_id].is_probably_copy
            ):
                raise DuplicatedIdError(
                    "caused by referecence, unproblematic", new_glob_id
                )
            else:
                raise DuplicatedIdError(f"problem with {new_glob_id}", new_glob_id)
        self.global_id = new_glob_id
        return self.global_id

    def get_global_id(self):
        if self.global_id is None:
            return self.create_global_id()
        else:
            return self.global_id

    def get_source_string(self):
        return etree.tostring(self.element).decode()

    def print_source(self):
        print(self.get_source_string())

    def check_4_empty_fields(self):
        global all_missing_fields
        global events_with_missing_field
        missing_vals = [
            field
            for field, val in vars(self).items()
            if (field not in Event.regulary_missing_fields and not bool(val))
        ]
        all_missing_fields += missing_vals
        if missing_vals:
            events_with_missing_field += 1
            print(f"\nobj {self.get_global_id()} ({self.type})")
            print(f"\nmissing: {', '.join(missing_vals)}")

    def return_places_labels(self):
        p_labels = []
        for p in self.places:
            p_labels.append(p["label"])
        return p_labels

    def get_places(self, places):
        unique_places = []
        for place in places:
            label = place.strip()
            p_id = places_index.get_id_for_label(label)
            unique_places.append({"id": p_id, "label": label})
        return unique_places

    def to_json(self):
        return {
            "id": self.get_global_id(),
            "type": self.type,
            "date": self.date,
            "place": self.places,
            "description": self.description,
            "file": self.file_identifier,
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
        file_identifier: str,
    ):
        super().__init__(
            _type,
            _id,
            date,
            place,
            description,
            xml_element,
            file_identifier,
            "trial_result",
        )

    def to_json(self):
        json_base_dict = super().to_json()
        json_extra_dict = {"xml": self.get_source_string()}
        json_extra_dict["place"] = [p["label"] for p in self.places]
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
        punishments_xml: list,
    ):
        super().__init__(
            _type,
            _id,
            date,
            place,
            description,
            xml_element,
            file_identifier,
            "trial_result",
        )
        self.punishments_xml = punishments_xml if punishments_xml else []
        self.methods: list = self.get_punishment_methods()
        self.carried_out = True if self.methods else False

    def get_punishment_methods(self):
        methods = []
        counter = 0
        for punishment in self.punishments_xml:
            counter += 1
            number = int(punishment.get("n")) if punishment.get("n") else counter
            label = label_short = label_ts = punishment.text.strip()
            if label in punishments_dict:
                label_short = label_ts = punishments_dict[label]
            if label_short in punishments_dict_ts:
                label_ts = punishments_dict_ts[label_short]
            p_id = punishment_index.get_id_for_label(label)
            if label in punishments_dict:
                label = punishments_dict[label]
            methods.append({"id": p_id,
                            "order": number,
                            "label": label,
                            "label_short": label_short,
                            "label_ts": label_ts})
        return methods

    def return_punishments_as_str(self):
        returner = []
        for punishment in self.methods:
            returner.append(punishment["label"])
        return returner

    def to_json(self):
        json_base_dict = super().to_json()
        # json_base_dict["date"] = self.date[0] if self.date else ""
        json_base_dict["place"] = [p["label"] for p in self.places]
        json_extra_dict = {
            "xml": self.get_source_string(),
            "methods": [m["label_ts"] for m in self.methods],
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
        methods_xml: list,
    ):
        super().__init__(
            _type,
            _id,
            date,
            place,
            description,
            xml_element,
            file_identifier,
            "trial_result",
        )
        self.methods_xml = methods_xml if methods_xml else []
        self.methods: list = self.get_execution_methods()
        self.carried_out = True if self.methods else False
        if len(place) > 1:
            input(place)

    def get_execution_methods(self):
        methods = []
        counter = 0
        for punishment in self.methods_xml:
            counter += 1
            number = int(punishment.get("n")) if punishment.get("n") else counter
            label = label_short = label_ts = punishment.text.strip()
            if label in punishments_dict:
                label_short = label_ts = punishments_dict[label]
            if label_short in punishments_dict_ts:
                label_ts = punishments_dict_ts[label_short]
            p_id = execution_index.get_id_for_label(label)
            if label in punishments_dict:
                label = punishments_dict[label]
            methods.append({"id": p_id,
                            "order": number,
                            "label": label,
                            "label_short": label_short,
                            "label_ts": label_ts})
        return methods

    def return_executions_as_str(self):
        returner = []
        for execution in self.methods:
            returner.append(execution["label"])
        return returner

    def to_json(self):
        json_base_dict = super().to_json()
        # json_base_dict["date"] = self.date[0] if self.date else ""
        json_base_dict["place"] = [p["label"] for p in self.places]
        json_extra_dict = {
            "xml": self.get_source_string(),
            "methods": [m["label_ts"] for m in self.methods],
        }
        return json_base_dict | json_extra_dict


# class Birth(Event):
#     type_key = "birth"

#     def __init__(
#             self,
#             _type: str,
#             _id: list,
#             date: list,
#             place: list,
#             description: list,
#             xml_element: etree._Element,
#             file_identifier: str,
#     ):
#         super().__init__(
#             _type,
#             _id,
#             date,
#             place,
#             description,
#             xml_element,
#             file_identifier,
#             "trial_result"
#         )


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
        decade_age: str,
        _type: str,
        marriage_status: str,
        faith: str,
        thumbnail: str,
        occupation: str,
        file_identifier: str,
        xml_element: etree._Element,
        doc: TeiReader,
    ):
        self.xml_id: str = xml_id
        self.id = xml_id if xml_id else ""
        if not self.id:
            Person.random_counter += 1
            self.id = f"{Person.random_counter:04}"
        self.roles: dict = dict([(file_identifier, role) for role in roles])
        self.forename: str = forename
        self.surname: str = surname
        self.birth_element: etree._Element = birth_element[0] if birth_element else None
        self.death_element: etree._Element = death_element[0] if death_element else None
        self._birth_place: str = None
        self.sex: str = sex
        self.age = age
        self.decade_age = decade_age
        self.refine_age()
        self.type: str = _type
        self.marriage_status: str = marriage_status
        self.faith: str = faith
        self.occupation: str = occupation
        self.global_id = None
        self.file_identifier = file_identifier
        self.related_events = []
        self.element: etree._Element = xml_element
        self.all_elements: list = [xml_element]
        # self.element_cp = deepcopy(self.element)
        self.typesense_sorter = 0
        self.fullname = ""
        self.archive_institutions = []
        self.doc: TeiReader = doc
        self.thumbnail = thumbnail
        self.rs = None
        self.translate_labels()

    def translate_labels(self):
        try:
            self.type = label_dict[self.type]
        except KeyError as e:
            if e.args[0] not in ["", None, "k. A.", "K. A."]:
                raise e
        try:
            self.sex = label_dict[self.sex]
        except KeyError as e:
            if e.args[0] not in ["", None, "k. A.", "K. A."]:
                raise e
        try:
            self.marriage_status = label_dict[self.marriage_status]
        except KeyError as e:
            if e.args[0] not in ["", None, "k. A.", "K. A."]:
                raise e
        try:
            self.faith = label_dict[self.faith]
        except KeyError as e:
            if e.args[0] not in ["", None, "k. A.", "K. A."]:
                raise e

    def refine_age(self):
        nmbrs = re.search(".*?([0-9]+).*", self.age)
        if nmbrs:
            self.age = nmbrs.group(1)
        elif re.search(".*?([0-9]+).*", self.decade_age):
            self.age = f"~{self.decade_age}0"
        else:
            self.age = "k.A."
        if int(self.decade_age) < 1:
            self.decade_age = "k. A."
        else:
            self.decade_age = f"{self.decade_age}0–{self.decade_age}9"

    def return_birth_place(self):
        if self._birth_place is None:
            if self.birth_element is not None:
                settlements = self.birth_element.xpath(
                    "tei:placeName/tei:settlement/text()", namespaces=tei_nsmp
                )
                country = self.birth_element.xpath(
                    "tei:placeName/tei:country/text()", namespaces=tei_nsmp
                )
                self._birth_place = ""
                self._birth_place += settlements[0].strip() if settlements else ""
                self._birth_place += f" ({country[0].strip()})" if country else ""
        if self._birth_place == "k. A. (k. A.)":
            self._birth_place = "k. A."
        return self._birth_place

    def create_global_id(self, override=False):
        if self.global_id is not None and not override:
            raise ValueError("logic error somewhere!", self.global_id)
        new_glob_id = (
            Person.global_id_prefix
            + Person.delim
            + self.file_identifier
            + Person.delim
            + self.id
        )
        try:
            check_global_id(new_glob_id)
        except DuplicatedIdError:
            if (
                self.is_probably_copy
                or global_events_by_ids[new_glob_id].is_probably_copy
            ):
                raise DuplicatedIdError(
                    "caused by referecence, unproblematic", new_glob_id
                )
            else:
                raise DuplicatedIdError(f"problem with {new_glob_id}", new_glob_id)
        self.global_id = new_glob_id
        return self.global_id

    def get_global_id(self):
        if self.global_id is None:
            return self.create_global_id()
        else:
            return self.global_id

    def to_xml(self):
        self.element.set(f"{{{xmlns}}}id", self.global_id)
        self.element.append(
            teiMaker.note(
                self.return_full_name(),
                type="label",
            )
        )
        return self.element

    def add_selfref_as_next(self):
        if self.rs is None:
            self.rs = teiMaker.rs(self.return_full_name(), ref="#" + self.global_id)
            self.element.addnext(self.rs)

    def append_related_event(self, event):
        self.related_events.append(event)

    def get_source_string(self):
        return etree.tostring(self.element).decode()

    def return_full_name(self) -> str:
        if self.fullname == "":
            if self.forename and self.surname:
                self.fullname = clear_kA(f"{self.forename} {self.surname}".strip())
            elif self.surname:
                self.fullname = clear_kA(self.surname)
            elif self.forename:
                self.fullname = clear_kA(self.forename)
            if not self.fullname:
                self.fullname = "k.A."
        return self.fullname

    def to_json(self):
        offences = []
        executions = []
        punishments = []
        execution_places = []
        for event in self.related_events:
            if isinstance(event, Offence):
                offence: Offence = event
                for o_obj in offence.return_offence_types():
                    offences.append(o_obj["label"])
            elif isinstance(event, Execution):
                execution: Execution = event
                for e_obj in execution.methods:
                    executions.append(e_obj["label"])
                execution_places += event.return_places_labels()
            elif isinstance(event, Punishment):
                punishment: Punishment = event
                for p_obj in punishment.methods:
                    punishments.append(p_obj["label"])
                # execution_places += event.places
            else:
                # hier gibt es einen Fall mit trial result
                pass
        return {
            "sorter": self.typesense_sorter,
            "global_id": self.global_id,
            "forename": self.forename,
            "surname": self.surname,
            "fullname": self.return_full_name(),
            "birth_place": self.return_birth_place(),
            # "roles": self.roles,
            "sex": self.sex,
            "age": self.age,
            "decade_age": self.decade_age,
            "type": self.type,
            "marriage_status": self.marriage_status,
            "faith": self.faith,
            "occupation": ", ".join([i.strip() for i in self.occupation]),
            "file_identifier": self.file_identifier,
            "related_events": [event.get_global_id() for event in self.related_events],
            "offences": list(set(offences)),
            "thumbnail": self.thumbnail,
            "execution": executions if executions else ["Keine"],
            "execution_places": execution_places,
            "punishments": punishments if punishments else ["Keine"],
            "id": self.get_global_id(),
            "archives": self.archive_institutions,
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
        raw_offence_types: list,
        tools: list,
    ) -> None:
        super().__init__(
            _type,
            _id,
            date,
            place,
            description,
            xml_element,
            file_identifier,
            "offence",
        )
        self.proven_by_persecution: bool = None
        self.completed: typing.Optional[bool] = None
        self.aided: typing.Optional[bool] = None
        self.raw_offence_types: list = raw_offence_types
        self.offence_types: list = None
        self.tools: list = []
        self.get_typed_tools(tools)
        self.set_offence_status()
        _ = self.return_offence_types()

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
            self.tools.append({"id": tool_id, "order": counter, "label": label})

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
            "tools": self.tools,
        }
        return json_base_dict | json_extra_dict

    def return_offence_types(self):
        if self.offence_types is None:
            self.offence_types = []
            counter = 0
            for offence in self.raw_offence_types:
                counter += 1
                offence_id = offence_index.get_id_for_label(offence.strip())
                self.offence_types.append(
                    {"id": offence_id, "order": counter, "label": offence}
                )
        return self.offence_types


def extract_person(
    person_element: etree._Element, file_identifier: str, nsmap: dict, doc: TeiReader
) -> Person:
    xml_id = person_element.xpath("@xml:id", namespaces=nsmap)
    roles = person_element.xpath("@role", namespaces=nsmap)
    forename = person_element.xpath(
        "./tei:persName/tei:forename/text()", namespaces=nsmap
    )
    surname = person_element.xpath(
        "./tei:persName/tei:surname//text()[normalize-space(.)!='']", namespaces=nsmap
    )
    birth_element = person_element.xpath("./tei:birth", namespaces=nsmap)
    death_element = person_element.xpath("./tei:death", namespaces=nsmap)
    sex = person_element.xpath("./tei:sex/@value", namespaces=nsmap)
    decade_age = person_element.xpath("./tei:age/@value", namespaces=nsmap)
    age = person_element.xpath("./tei:age/text()", namespaces=nsmap)
    _type = person_element.xpath("./tei:state/@type", namespaces=nsmap)
    marriage_state = person_element.xpath(
        "./tei:state/tei:desc//text()", namespaces=nsmap
    )[0]
    faith = person_element.xpath("./tei:faith/text()", namespaces=nsmap)[0]
    occupation = person_element.xpath("./tei:occupation/text()", namespaces=nsmap)
    thumbnail = doc.any_xpath("//tei:pb/@facs")[0]
    person_obj = Person(
        xml_id=xml_id[0] if xml_id else "",
        roles=roles,
        forename=forename[0].strip() if forename else "",
        surname=surname[0].strip() if surname else "",
        birth_element=birth_element,
        # these are always empty!
        death_element=death_element,
        sex=sex[0].strip() if sex else "",
        age=age[0].strip() if age else "",
        decade_age=decade_age[0].strip() if decade_age else "0",
        _type=_type[0] if _type else "",
        marriage_status=marriage_state.strip(),
        faith=faith.strip(),
        occupation=occupation,
        thumbnail=thumbnail,
        file_identifier=file_identifier,
        xml_element=person_element,
        doc=doc,
    )
    try:
        person_obj.create_global_id()
    except ValueError as e:
        input(e)
    return person_obj


def extract_event(event_element: etree._Element, file_identifier: str, nsmap: dict):
    event_type: str = event_element.xpath("./@type", namespaces=nsmap)[0]
    xml_id: list = event_element.xpath("./@xml:id", namespaces=nsmap)
    if not xml_id:
        xml_id: list = event_element.xpath("./@ref", namespaces=nsmap)
        if xml_id and xml_id[0] != "#":
            xml_id = [f"#{xml_id[0]}"]
    dates: list = []
    date: list = event_element.xpath("./tei:desc/tei:date", namespaces=nsmap)
    if len(date) == 2:
        print(f"multiple dates in {xml_id}")
        date1, date2 = event_element.xpath("./tei:desc/tei:date", namespaces=nsmap)
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
                    namespaces=nsmap,
                )[0]
                dates.append(date_exec)
            except IndexError:
                try:
                    date_exec = date1.xpath(
                        """ancestor::tei:person/tei:event[@type='verdict']
                        /tei:desc/tei:date/@when""",
                        namespaces=nsmap,
                    )[0]
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
                    namespaces=nsmap,
                )[0]
                dates.append(date_exec)
            except IndexError:
                try:
                    date_exec = date[0].xpath(
                        """ancestor::tei:person/tei:event[@type='verdict']
                        /tei:desc/tei:date/@when""",
                        namespaces=nsmap,
                    )[0]
                    dates.append(date_exec)
                except IndexError:
                    date_exec = ""
                    dates.append(date_exec)
            if "after" in date_when:
                dates.append(re.sub(r"\s+", " ", date_when).strip())
    else:
        print("no date or more than two dates in ", xml_id)
    place: list = event_element.xpath(
        "./tei:desc/tei:placeName/text()[1]", namespaces=nsmap
    )
    description_str: list = event_element.xpath(
        "./tei:desc/tei:desc//text()", namespaces=nsmap
    )
    event_obj = None
    if event_type in Event.xml_offence_types:
        try:
            typed_offences: list = event_element.xpath(
                """./tei:desc/tei:trait[@type='typeOfOffence']/
                tei:desc/tei:list/tei:item/text()""",
                namespaces=nsmap,
            )
            typed_tools: list = event_element.xpath(
                """./tei:desc/tei:trait[@type='toolOfCrime']
                /tei:desc//text()""",
                namespaces=nsmap,
            )
            event_obj = Offence(
                _type=event_type,
                _id=xml_id,
                date=dates,
                place=place,
                description=description_str,
                xml_element=event_element,
                file_identifier=file_identifier,
                raw_offence_types=typed_offences,
                tools=typed_tools,
            )
        except DuplicatedIdError as e:
            if "unproblematic" in e.args[0]:
                existing_event_id = e.args[1]
                return existing_event_id
            else:
                raise e
    elif event_type in Event.xml_trial_result_types:
        punishments_xml = event_element.xpath(
            ".//tei:desc/tei:list/tei:item", namespaces=nsmap
        )
        if not punishments_xml:
            punishments_xml = event_element.xpath(
                ".//tei:desc//tei:desc", namespaces=nsmap
            )
        for element in punishments_xml:
            if element.text in punishments_dict:
                element.text = punishments_dict[element.text]
        try:
            print(Punishment.type_key)
            if event_type in (Punishment.type_key, Execution.type_key):
                event_obj = Punishment(
                    _type=event_type,
                    _id="",  # ids not necessary there
                    date=dates,
                    place=place,
                    description=description_str,
                    xml_element=event_element,
                    file_identifier=file_identifier,
                    punishments_xml=punishments_xml,
                )
            else:
                event_obj = TrialResult(
                    _type=event_type,
                    _id="",  # ids not necessary there
                    date=dates,
                    place=place,
                    description=description_str,
                    xml_element=event_element,
                    file_identifier=file_identifier,
                )
        except DuplicatedIdError as e:
            if "unproblematic" in e.args[0]:
                return e.args[1]
            else:
                raise e
    return event_obj


def change_relations(doc: TeiReader):
    id_has_active_relations = {}
    id_has_passive_relations = {}
    id_is_mentioned_in_relation = {}
    for relation in doc.any_xpath("//tei:relation"):
        active_el = deepcopy(relation)
        passive_el = deepcopy(relation)
        active_id = active_el.attrib.pop("active").removeprefix("#")
        passive_id = passive_el.attrib.pop("passive").removeprefix("#")
        if active_id not in id_has_active_relations:
            id_has_active_relations[active_id] = []
        id_has_active_relations[active_id].append(active_el)
        if passive_id not in id_has_passive_relations:
            id_has_passive_relations[passive_id] = []
        id_has_passive_relations[passive_id].append(passive_el)
        if active_id not in id_is_mentioned_in_relation:
            id_is_mentioned_in_relation[active_id] = []
        if passive_id not in id_is_mentioned_in_relation:
            id_is_mentioned_in_relation[passive_id] = []
        id_is_mentioned_in_relation[passive_id].append(active_el)
        id_is_mentioned_in_relation[active_id].append(passive_el)
        parent = relation.getparent()
        parent.remove(relation)
    for active_id, relation_elements in id_has_passive_relations.items():
        active_xpath_expression = f"//tei:event[@xml:id='{active_id}']"
        try:
            if active_id == "execution":
                active_el = doc.any_xpath(f"//tei:event[@type='{active_id}']")[0]
            else:
                active_el = doc.any_xpath(active_xpath_expression)[0]
            for rel_el in relation_elements:
                active_el.append(rel_el)
        except IndexError:
            pass
    for passive_id, relation_elements in id_has_active_relations.items():
        passive_xpath_expression = f"//tei:event[@xml:id='{passive_id}']"
        try:
            if passive_id == "execution":
                passive_el = doc.any_xpath(f"//tei:event[@type='{passive_id}']")[0]
            else:
                passive_el = doc.any_xpath(passive_xpath_expression)[0]
            for rel_el in relation_elements:
                passive_el.append(rel_el)
        except IndexError:
            pass
    return id_is_mentioned_in_relation


def update_id_in_relations(event: Event, id_to_be_replaced, elements: list):
    for el in elements:
        el: etree._Element
        if el.get("active") == id_to_be_replaced:
            el.set("active", f"#{event.global_id}")
        if el.get("passive") == id_to_be_replaced:
            el.set("passive", f"#{event.global_id}")


def extract_events_and_persons(doc: TeiReader, file_identifier: str):
    events = []
    persons = []
    event_id_mentioned_in_relation = change_relations(doc)
    for person_element in doc.any_xpath("//tei:person"):
        person_obj: Person = extract_person(
            person_element, file_identifier, doc.nsmap, doc
        )
        person_obj.archive_institutions = doc.any_xpath(
            "//tei:msIdentifier/tei:institution/text()"
        )
        persons.append(person_obj)
        for event_element in person_element.xpath(".//tei:event", namespaces=doc.nsmap):
            event_obj = extract_event(event_element, file_identifier, doc.nsmap)
            if event_obj:
                if isinstance(event_obj, str):
                    event_obj = global_events_by_ids[event_obj]
                    event_obj.element_copies.append(event_element)
                    person_obj.append_related_event(event_obj)
                else:
                    events.append(event_obj)
                    person_obj.append_related_event(event_obj)
                if event_obj.id in event_id_mentioned_in_relation:
                    elements = event_id_mentioned_in_relation[event_obj.id]
                    update_id_in_relations(event_obj, "#" + event_obj.id, elements)
                elif isinstance(event_obj, Execution):
                    if "execution" in event_id_mentioned_in_relation:
                        elements = event_id_mentioned_in_relation["execution"]
                        update_id_in_relations(event_obj, "#execution", elements)
    return events, persons


def print_to_json(objects, category):
    object_json = dict((obj.get_global_id(), obj.to_json()) for obj in objects)
    fp = f"{json_file_output}/{category}.json"
    with open(fp, "w") as f:
        print(f"writing to {fp}")
        json.dump(object_json, f, indent=4)
    return object_json


def print_typesense_entries_to_json(documents):
    doc_json = dict()
    for doc in documents:
        doc: XmlDocument
        key = doc.get_global_id()
        val = doc.return_prescribed_typesense_entry()
        doc_json[key] = val
    fp = f"{json_file_output}/typesense_entries.json"
    with open(fp, "w") as f:
        print(f"writing to {fp}")
        json.dump(doc_json, f, indent=4)


def print_indices_to_json():
    for index in typed_indices:
        with open(f"{json_file_output}/unique_{index.id_prefix}.json", "w") as f:
            json.dump(index.ids_2_labels, f, indent=4)


def write_xml(objs, list_element, path, template):
    print(f"writing {len(objs)} items to xml")
    for obj in objs:
        obj.add_selfref_as_next()
        obj_xml = obj.to_xml()
        list_element.append(obj_xml)
    print(f"writing to {path}")
    template.tree_to_file(path)


def print_index_to_xml(name: str, objs: list):
    template = TeiReader(f"./template/{name}.xml")
    out_fp = f"{xml_index_output}/{name}.xml"
    xpath = ".//tei:listPerson" if name == "listperson" else ".//tei:listEvent"
    list_element = template.any_xpath(xpath)[0]
    if name == "listperson":
        objs.sort(key=lambda po: po.fullname)
    write_xml(objs, list_element, out_fp, template)


def prepare_output_folder():
    old_files = glob.glob(f"./{json_file_output}/*.json")
    for old_file in old_files:
        os.remove(old_file)
    os.makedirs(json_file_output, exist_ok=True)


class XmlDocument:
    def __init__(
        self,
        xml_tree: TeiReader,
        path: str,
        identifier: str,
        events: list,
        persons: list,
    ):
        self.xml_tree: TeiReader = xml_tree
        self.path: str = path
        self.id: str = identifier
        self.global_id = None
        self.events: list = events
        self.executions: list = [e for e in events if isinstance(e, Execution)]
        self.punishments: list = [e for e in events if isinstance(e, Punishment)]
        self.trialresults: list = [e for e in events if isinstance(e, TrialResult)]
        self.persons: list = persons
        self.fulltext: str = self.return_doc_text()
        self.title: str = self.return_title()
        self.date: str = ""
        self.pubPlace: str = ""
        self.publisher: str = ""
        self.sorting_date = None
        self.label_year = None
        self.get_bibl_data()
        self.archive_institutions = []
        self.archive_signatures = []
        self.get_archive_data()

    def return_thumbnail_name(self):
        return self.xml_tree.any_xpath("//tei:pb/@facs")[0]

    # def export_verticals(self, output_dir: str):
    #     verticals = mk_verticals.export_verticals_from_doc(
    #         doc=self.xml_tree,
    #         title=self.title,
    #         doc_id=self.get_global_id(),
    #         date=self.return_sorting_date(),
    #     )
    #     file_ext = ".tsv"
    #     output_dir = output_dir + \
    #         "/" if not output_dir.endswith("/") else output_dir
    #     outfile_path = f"{output_dir}{self.id}{file_ext}"
    #     with open(outfile_path, "w") as of:
    #         of.write(verticals)

    def get_archive_data(self):
        for witness in self.xml_tree.any_xpath("//tei:msDesc"):
            arch_i = witness.xpath(
                ".//tei:msIdentifier/tei:institution/text()",
                namespaces=self.xml_tree.nsmap,
            )
            # these are mostly wrong, creating bad data
            # arch_s = witness.xpath(
            #     ".//tei:msIdentifier/tei:settlement/text()",
            #     namespaces=self.xml_tree.nsmap
            # )
            arch_sig = witness.xpath(
                ".//tei:settlement/tei:idno[@type='signatory']/text()",
                namespaces=self.xml_tree.nsmap,
            )
            insti_string = arch_i[0] if arch_i else ""
            # if arch_s:
            #     insti_string = f"{insti_string}, {arch_s[0]}"
            self.archive_institutions.append(insti_string)
            self.archive_signatures.append(f"{arch_sig} ({arch_i})")

    def get_bibl_data(self):
        self.print_dates: list = self.xml_tree.any_xpath(
            "//tei:sourceDesc//tei:biblStruct//tei:date/@when"
        )
        if self.print_dates:
            self.print_dates = [date.strip(" .") for date in self.print_dates]
        self.pubPlace = self.xml_tree.any_xpath(
            "//tei:sourceDesc//tei:biblStruct//tei:pubPlace/text()"
        )[0]
        if self.pubPlace in places_dict:
            self.pubPlace = places_dict[self.pubPlace]
        self.publisher = self.xml_tree.any_xpath(
            "//tei:sourceDesc//tei:biblStruct//tei:publisher/text()"
        )[0]
        if self.publisher in publishers_dict:
            self.publisher = publishers_dict[self.publisher]

    def return_title(self):
        return extract_fulltext(
            self.xml_tree.any_xpath("//tei:title")[0],
        )

    def return_doc_text(self):
        text_el = deepcopy(self.xml_tree.any_xpath("//tei:text")[0])
        bs_text = text_el.xpath(
            "//tei:app//tei:rdg|//tei:sic",
            namespaces=tei_nsmp,
        )
        for bs in bs_text:
            bs.getparent().remove(bs)
        return extract_fulltext(
            text_el,
            tag_blacklist=[
                "{http://www.tei-c.org/ns/1.0}fs",
                "{http://www.tei-c.org/ns/1.0}f",
                "{http://www.tei-c.org/ns/1.0}figDesc",
            ],
        )

    def get_global_id(self):
        if self.global_id is None:
            try:
                check_global_id(self.id)
            except DuplicatedIdError:
                input(f"Document id '{self.id}' used more then once.")
                raise ValueError
            self.global_id = self.id
        return self.global_id

    def to_json(self):
        persons = [p.get_global_id() for p in self.persons]
        events = [e.get_global_id() for e in self.events]
        return {
            "title": self.title,
            "id": self.get_global_id(),
            "filename": self.path.split("/")[-1],
            "contains_persons": persons,
            "contains_events": events,
            "fulltext": self.fulltext,
            "archives": self.archive_institutions,
        }

    def return_sorting_date(self):
        if self.sorting_date is None:
            nmbr_dates = []
            dates = [e.date[0] for e in self.punishments if e.date]
            dates += [e.date[0] for e in self.executions if e.date]
            dates += [e.date[0] for e in self.trialresults if e.date]
            dates += self.print_dates
            for date in dates:
                if re.search(r"\d", date):
                    try:
                        numeric_date_str = re.sub(r"[-\ .]*", "", date).strip()
                        if (
                            re.search("[A-Za-z]+", numeric_date_str)
                            and numeric_date_str[-4:].isnumeric()
                        ):
                            numeric_date_str = numeric_date_str[-4:]
                        nmbr_dates.append(int(f"{numeric_date_str:<08}"))
                    except ValueError:
                        pass
            if nmbr_dates:
                self.sorting_date = sorted(nmbr_dates)[-1]
            else:
                self.sorting_date = 0000
        return self.sorting_date

    def return_label_year(self):
        if self.label_year is None:
            sorting_date = self.return_sorting_date()
            if sorting_date != 0:
                self.label_year = int(str(sorting_date)[0:4])
            else:
                self.label_year = 1700
        return self.label_year

    def return_prescribed_typesense_entry(self):
        # events_ids = [e.get_global_id() for e in self.events]
        return {
            "thumbnail": self.return_thumbnail_name(),
            "sorting_date": self.return_sorting_date(),
            "label_date": self.return_label_year(),
            "title": self.title,
            "id": self.get_global_id(),
            "filename": self.path.split("/")[-1],
            "fulltext": self.fulltext,
            "print_date": self.print_dates[0] if self.print_dates else "k. A.",
            "printer": self.publisher,
            "printing_location": self.pubPlace,
            "archives": self.archive_institutions,
        }

    def return_typesense_entry(self):
        events_ids = [e.get_global_id() for e in self.events]
        return {
            "thumbnail": self.return_thumbnail_name(),
            "sorting_date": self.return_sorting_date(),
            "title": self.title,
            "id": self.get_global_id(),
            "filename": self.path.split("/")[-1],
            "contains_persons": [p.to_json() for p in self.persons],
            "contains_events": events_ids,
            "fulltext": self.fulltext,
            "print_date": self.print_dates[0] if self.print_dates else "",
            "execution_date": self.executions[0].date if self.executions else "",
            "execution_methods": [
                ex.return_executions_as_str() for ex in self.executions
            ],
            "punishment_methods": [
                pun.return_punishments_as_str() for pun in self.punishments
            ],
            "archives": self.archive_institutions,
        }

    def write_changes(self):
        filename = self.path.split("/")[-1]
        new_path = f"{xml_editions_output}/{filename}"
        tidy_readings(self.xml_tree)
        print(f"creating {new_path}")
        self.xml_tree.tree_to_file(new_path)


# def export_all_verticals(xml_docs, verticals_output_folder):
#     for doc in xml_docs:
#         doc.export_verticals(verticals_output_folder)


def resort_persons_for_typesense(person_objs: list):
    person_objs.sort(key=lambda pers_o: (pers_o.surname, pers_o.forename))
    c = 0
    for person_obj in person_objs:
        c += 1
        person_obj.typesense_sorter = c
    return person_objs


if __name__ == "__main__":
    event_objs = []
    person_objs = []
    events_json = {}
    xml_docs = []
    # verticals_output_folder = mk_verticals.prepare_output_dir()
    # template_doc = TeiReader("template/events.xml")
    # listevent = template_doc.any_xpath(
    # ".//tei:listEvent[@type='offences']")[0]
    for file_path in glob.glob(cases_dir):
        # file_identifier = file_path.split("/")[-1]
        doc_id = re.match(".*?/([^/]+).xml", file_path).group(1)
        print(file_path)
        try:
            tei_doc = TeiReader(file_path)
            entity_objects = extract_events_and_persons(tei_doc, doc_id)
            event_objs += entity_objects[0]
            person_objs += entity_objects[1]
            xml_doc = XmlDocument(
                tei_doc,
                file_path,
                doc_id,
                entity_objects[0],
                entity_objects[1],
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
            event: Offence
            _ = event.return_offence_types()
        else:
            if event in punishments_dict_ts:
                event = punishments_dict_ts[event]
            punishment_objects.append(event)
        event.check_4_empty_fields()

    prepare_output_folder()
    # template_doc.tree_to_file(f"{xml_file_output}/events.xml")
    print_to_json(offences_objects, "offences")
    print_to_json(punishment_objects, "punishments")
    print_to_json(resort_persons_for_typesense(person_objs), "persons")
    print_to_json(xml_docs, "documents")
    # export_all_verticals(xml_docs, verticals_output_folder)
    print_typesense_entries_to_json(xml_docs)
    missing_fields = ", ".join(list(set(all_missing_fields)))
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
    all_events = global_events_by_ids.values()
    offence_list = list(event for event in all_events if event.type == "offence")
    punishment_list = list(event for event in all_events if event.type != "offence")
    # event_list = list(
    #     global_events_by_ids.values()
    # )
    # event_list.sort(
    #     key=lambda e: e.type
    # )
    # print_index_to_xml(
    #     name="events",
    #     objs=event_list
    # )
    print_index_to_xml(name="offences", objs=offence_list)
    print_index_to_xml(name="punishments", objs=punishment_list)
    print_index_to_xml(name="listperson", objs=person_objs)
    for xml_doc in xml_docs:
        xml_doc: XmlDocument
        xml_doc.write_changes()
