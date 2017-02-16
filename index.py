from awslambda import awslambda
from sqs import sqs
from sns import sns
from s3 import s3
from kms import kms
from iam import iam
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
import traceback

# Environment Variables
config = ConfigParser.RawConfigParser()
if os.path.exists("defaults.ini"):
    config.read('defaults.ini')
else:
    config.read('default.ini')

dynamodb = boto3.resource('dynamodb')
s3Client = boto3.client('s3')


def handler(event, context):
    t = Template()
    iamTemplate = None
    for record in event['Records']:

        t.add_version("2010-09-09")
        applicationName = ""
        try:
            print(record)
            applicationName = record['dynamodb']['NewImage']['ApplicationName']['S']
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
                    iamTemplate = iam(item, iamTemplate, defaults=config)

                template = StringIO(yaml.safe_dump(json.loads(t.to_json()), None, allow_unicode=True))
                s3Client.put_object(
                    Bucket=config.get('DEFAULT', 'CloudformationBucket'),
                    Key=applicationName + "/" + applicationName + ".template",
                    Body=template.read()
                )
                template.close()

                template = StringIO(yaml.safe_dump(json.loads(t.to_json()), None, allow_unicode=True))
                myzip = zipfile.ZipFile(applicationName + ".zip", 'w')
                myzip.writestr(config.get('WriteFileDirectory') + applicationName + ".template", template.read())
                myzip.close()
                template.close()

                with open(applicationName + ".zip", "rb") as myzip:
                    s3Client.put_object(
                        Bucket=config.get('DEFAULT', 'CloudformationBucket'),
                        Key=applicationName + "/" + applicationName + ".zip",
                        Body=myzip.read()
                    )

                if iamTemplate is not None:
                    template = StringIO(yaml.safe_dump(json.loads(iamTemplate.to_json()), None, allow_unicode=True))
                    s3Client.put_object(
                        Bucket=config.get('DEFAULT', 'CloudformationBucket'),
                        Key=applicationName + "/" + applicationName + "-IAM.template",
                        Body=template.read()
                    )
                    template.close()

                    template = StringIO(yaml.safe_dump(json.loads(iamTemplate.to_json()), None, allow_unicode=True))
                    myzip = zipfile.ZipFile(applicationName + "-IAM.zip", 'w')
                    myzip.writestr(config.get('WriteFileDirectory') + applicationName + "-IAM.template",
                                   template.read())
                    myzip.close()
                    template.close()

                    with open(applicationName + "-IAM.zip", "rb") as myzip:
                        s3Client.put_object(
                            Bucket=config.get('DEFAULT', 'CloudformationBucket'),
                            Key=applicationName + "/" + applicationName + "-IAM.zip",
                            Body=myzip.read()
                        )

        except Exception, e:
            print("Unexpected error:", sys.exc_info()[0])
            print("Couldn't do it: %s" % e)
            traceback.print_exc()
            return {}
