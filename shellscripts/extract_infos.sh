#!/bin/bash
# installs requirements and runs script(s) to extract infos from xmls
pip install -r ./pyscripts/requirements.txt
python ./pyscripts/extract_data.py
person_index_path="./out/xml/indices/*.xml"
editions_path="./out/xml/editions/*.xml"
mentions-to-indices -t "erwähnt in " -i "$person_index_path" -f "$editions_path" --title-xpath "//tei:title/text()"
