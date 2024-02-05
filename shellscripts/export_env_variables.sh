env_file="secret.env"
if [ -f $env_file ]; 
then
    export $(grep -v '^#' secret.env | xargs)
else
    echo "GITLAB_SOURCE_TOKEN=''" >> $env_fileex
    echo "please provide credentials in a totally secure file (${env_file}) (allready created)"
fi