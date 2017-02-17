from awslambda import awslambda
from sqs import sqs
from sns import sns
from s3 import s3
from kms import kms
from iam import iam
from dynamodb import dynamodb
from troposphere import Template
from boto3.dynamodb.conditions import Key
from cStringIO import StringIO
import ConfigParser
import boto3
import yaml
import json
import sys
import os
import zipfile

# Environment Variables

config = ConfigParser.RawConfigParser()
if os.path.exists("defaults.ini"):
    config.read('defaults.ini')
else:
    config.read('default.ini')

dynamodb = boto3.resource('dynamodb')
s3Client = boto3.client('s3')

t = Template()

t.add_version("2010-09-09")
applicationName = "BKR"
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
    if item['Protocol'] == "dynamodb":
        t = dynamodb(item, t, defaults=config)
    if item['Protocol'] == "iam":
        iamTemplate = Template()
        iamTemplate.add_version("2010-09-09")
        iamTemplate = iam(item, iamTemplate, defaults=config)
        # print(yaml.safe_dump(json.loads(iamTemplate.to_json()), None, allow_unicode=True))

print(yaml.safe_dump(json.loads(t.to_json()), None, allow_unicode=True))
