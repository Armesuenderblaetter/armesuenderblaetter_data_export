[![Linting](https://github.com/Armesuenderblaetter/data/workflows/Lint/badge.svg)](https://github.com/Armesuenderbblaetter/data/workflows/Lint/badge.svg)

This repo provides a local copy of the armesuenderblaetter-data-repo from gh.
For testing
1. clone this repo
2. create a virtual environment for python; eg. 
        `python3 -m venv $dir_name` & 
        `source $dir_name/bin/activate`
3. check if your python virtual environment is up
4. install pre-commit for hooks: `pip install pre-commit && pre-commit install`
6. run `./shellscripts/download_gitlab_data.sh` locally from base dir
7. add gitlab token to the created .env file
8. run `./shellscripts/download_gitlab_data.sh` again

See generated outputs [here](https://github.com/Armesuenderblaetter/armesuenderblaetter_data_ouput).
