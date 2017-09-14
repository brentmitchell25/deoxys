aws cloudformation create-stack --stack-name CloudformationGenerator --template-body file://init.yaml --capabilities CAPABILITY_NAMED_IAM --parameters ParameterKey=CloudformationBucket,ParameterValue=BUCKET_NAME ParameterKey=LambdaSubnetIds,ParameterValue=sg-********\\,sg-******** ParameterKey=LambdaSecurityGroups,ParameterValue=subnet-********\\,subnet-********\\,subnet-********
aws cloudformation wait stack-create-complete --stack-name CloudformationGenerator
pip install virtualenv
cd cloudformation-generator
source /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv cloudformation-generator
workon cloudformation-generator
pip install -r ../requirements.txt
bash ../deploy.sh
