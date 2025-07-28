#!/bin/bash
rm -rf cloned_repo out
./shellscripts/dl_and_prepare_gl_data.sh
./pyscripts/extract_data.py
./pyscripts/extract_verticals.py
mkdir cloned_repo
git clone https://github.com/Armesuenderblaetter/armesuenderblaetter_data_ouput.git cloned_repo
cp -r out/* cloned_repo/
cd cloned_repo
git add .
git commit -m "$(date) new data"
status=`git status`
if [[ $status == *"branch is ahead of"* ]]; then
	git push
else
        echo "nothing to push"
fi



