#!/bin/bash
# get gitlab token & define some vars
export_script="./shellscripts/export_env_variables.sh"
source $export_script
if [ -z $GITLAB_SOURCE_TOKEN ]
then
    echo "gitlab token not provided"
    exit 1
fi
gitlab_project_id='262'
gitlab_api_base_url='https://gitlab.oeaw.ac.at/api/v4/projects/'
gitlab_api_request='/repository/archive?'
output_archive="./asb.tar.gz"
custom_output_dir="./asb_master/"

# download and unzip
# rm old data / create target dir
if [ -d $custom_output_dir ]; then rm -fr $custom_output_dir; fi
mkdir -p $custom_output_dir
# to get an overview of what you could do with API/Token, use:
# curl "${gitlab_api_base_url}?private_token=${gitlab_token}"
# get the data via api
curl --header "PRIVATE-TOKEN: ${GITLAB_SOURCE_TOKEN}" "${gitlab_api_base_url}${gitlab_project_id}${gitlab_api_request}" --output $output_archive
# curl "${gitlab_api_base_url}${gitlab_project_id}${gitlab_api_request}private_token=${GITLAB_SOURCE_TOKEN}" --output $output_archive
# find out, how the api named the parent folder in the archive
top_level_folder_name="./"`tar -tzf $output_archive | head -1 | cut -f1 -d"/"`
# unzip the archive
tar -xvzf $output_archive
# check if the predicted folder name exists
if [ -d $top_level_folder_name ]
then 
    # move files from the archives parent folder to predictable custom folder
    mv $top_level_folder_name/* $custom_output_dir
    # remove parent folder from api dump
    rm -fr $top_level_folder_name
fi
# remove the archive file, if existing
if [ -f $output_archive ]; then rm $output_archive; fi

# rename some files for arche/processing
pyscripts/renameFiles.py
add-attributes -g $custom_output_dir"/303_annot_tei/*.xml" -b "."
pyscripts/add_ids.py
