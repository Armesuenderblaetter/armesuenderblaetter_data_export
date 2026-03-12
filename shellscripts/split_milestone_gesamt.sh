#!/bin/bash

# remove TEI namespace from root element before splitting
uv run pyscripts/remove_namespace.py

# split files
uv run pyscripts/milestone.py -t pb -a type_primary -n source asb_master/303_annot_tei_modified/*.xml
uv run pyscripts/milestone.py -t pb -a type_secondary -n source asb_master/303_annot_tei_modified/*.xml
uv run pyscripts/milestone.py -t pb -a edRef_#wb2 -n source asb_master/303_annot_tei_modified/*.xml

# cleanup to remove namespaces for id elements and save if data/editions
uv run pyscripts/cleanup.py