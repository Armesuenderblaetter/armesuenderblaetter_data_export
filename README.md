[![Linting](https://github.com/Flugblatter/data/workflows/Lint/badge.svg)](https://github.com/Flugblatter/data/workflows/Lint/badge.svg)

This repo provides a local copy of the flugblatt-data-repo from gh.
For testing
1. clone this repo
2. create a virtual environment for python; eg. 
        `python3 -m venv $dir_name` & 
        `source $dir_name/bin/activate`
3. check if your python virtual environment is up
4. run `./shellscripts/download_gitlab_data.sh` locally from base dir
5. add gitlab token to the created .env file
6. run `./shellscripts/download_gitlab_data.sh` again

(To test the export function run ./shellscripts/extract_infos.sh. Run this only in a virtual python environment!!)
