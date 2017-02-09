from awslambda import awslambda
from sqs import sqs
from sns import sns
from s3 import s3
from kms import kms
from iam import iam
from troposphere import Parameter, Ref, Template
from boto3.dynamodb.conditions import Key, Attr
import boto3
import yaml
import json
import configparser

# Environment Variables

config = configparser.ConfigParser()
config.read('defaults.ini')
config = config['DEFAULT']
dynamodb = boto3.resource('dynamodb')

t = Template()

t.add_version("2010-09-09")
applicationName = "SFTP"
protocols = dynamodb.Table('Application').query(
    KeyConditionExpression=Key('ApplicationName').eq(applicationName)
)
resources = {}
for item in protocols['Items']:
    if item['Protocol'] == "lambda":
        t = awslambda(item, t, defaults=config)
    if item['Protocol'] == "sqs":
        t = sqs(item, t, defaults=config)
    if item['Protocol'] == "sns":
        t = sns(item, t, defaults=config)
    if item['Protocol'] == 's3':
        t = s3(item, t, defaults=config)
    if item['Protocol'] == "kms":
        t = kms(item, t, defaults=config)
    if item['Protocol'] == "iam":
        iamTemplate = Template()
        iamTemplate.add_version("2010-09-09")
        iamTemplate = iam(item, t, defaults=config)


print(yaml.safe_dump(json.loads(t.to_json()), None, allow_unicode=True))
