cd cloudformation-generator
cwd=$(pwd)
source /usr/local/bin/virtualenvwrapper.sh
workon cloudformation-generator
rm bundle.zip
zip -9 bundle.zip default*
zip -r9 bundle.zip *.py
zip -r9 bundle.zip AWS_Simple_Icons/*
cd $VIRTUAL_ENV/lib/python2.7/site-packages
zip -r9 $cwd/bundle.zip *
cd $VIRTUAL_ENV/lib64/python2.7/site-packages
zip -r9 $cwd/bundle.zip *
cd $cwd
aws lambda update-function-code --function-name CloudformationGenerator --zip-file fileb://bundle.zip --no-verify-ssl
