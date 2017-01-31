from troposphere.constants import NUMBER
from awslambda import awslambda
from sqs import sqs
from sns import sns
from s3 import s3
from troposphere import Parameter, Ref, Template
from boto3.dynamodb.conditions import Key, Attr
from cStringIO import StringIO
import awacs.sqs as sqs
import configparser
import boto3
import yaml
import json
import sys
import pickle

# Environment Variables
receiveMessageWaitTimeSeconds = 20
messageRetentionPeriod = 604800

config = configparser.ConfigParser()
config.read('defaults.ini')
config = config['DEFAULT']

dynamodb = boto3.resource('dynamodb')
s3Client = boto3.client('s3')


def handler(event, context):
    t = Template()
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

                # template = open(applicationName + ".template", "w")
                # template.write(t.to_json())
                # template.write(yaml.safe_dump(json.loads(t.to_json()), None, allow_unicode=True))
                template = StringIO(yaml.safe_dump(json.loads(t.to_json()), None, allow_unicode=True))
                s3Client.put_object(
                    Bucket=config['CloudformationBucket'],
                    Key=applicationName + "/" + applicationName + ".template",
                    Body=template.read()
                )
                template.close()
        except:
            print("Unexpected error:", sys.exc_info()[0])
            return {}

