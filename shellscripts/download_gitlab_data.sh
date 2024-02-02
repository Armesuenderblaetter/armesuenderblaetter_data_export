# paste your token here
gitlab_token=''
gitlab_project_id='262'
gitlab_api_base_url='https://gitlab.oeaw.ac.at/api/v4/projects/'
gitlab_api_request='/repository/archive?'
output_archive="./flugblatter.tar.gz"
custom_output_dir="./todesurteile_master/"
# rm old data / create target dir
if [ -d $custom_output_dir ]; then rm -r $custom_output_dir; fi
mkdir $custom_output_dir
# to get an overview of what you could do with API/Token, use:
# curl "${gitlab_api_base_url}?private_token=${gitlab_token}"
# get the data via api
curl "${gitlab_api_base_url}${gitlab_project_id}${gitlab_api_request}private_token=${gitlab_token}" --output $output_archive
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
    rm -r $top_level_folder_name
fi
# remove the archive file, if existing
if [ -f $output_archive ]; then rm $output_archive; fi