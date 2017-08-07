from awslambda import awslambda
from sqs import sqs
from sns import sns
from s3 import s3
from kms import kms
from iam import iam
from stepfunctions import stepfunctions
from dynamodb import dynamodb
from troposphere import Template
from boto3.dynamodb.conditions import Key
from cStringIO import StringIO
import ConfigParser
import boto3
from cfn_flip import to_yaml
import json
import networkx as nx
import os
import uuid
import zipfile
import traceback
import re

regex = re.compile('[^a-zA-Z0-9]')

# Environment Variables
config = ConfigParser.RawConfigParser()
if os.path.exists("defaults.ini"):
    config.read('defaults.ini')
else:
    config.read('default.ini')

dynamodbClient = boto3.resource('dynamodb')
s3Client = boto3.client('s3')


def dependsOn(node, graph):
    retVal = []
    for u, v in graph.edges_iter():
        if node == u:
            retVal.append(regex.sub("", v))
    return retVal


def writeTemplate(template, graph):
    for node in graph:
        depends = dependsOn(node, graph)
        if depends != [] and 'resource' in graph.node[node]:
            graph.node[node]['resource'].__setattr__('DependsOn', dependsOn(node, graph=graph))
        print(str(graph.node[node]))
        template.add_resource(graph.node[node]['resource'])


def handler(event, context):
    t = Template()
    G = nx.DiGraph()
    iamTemplate = None
    retVal = []
    for record in event['Records']:
        print(record)
        t.add_version("2010-09-09")
        applicationName = ''
        try:
            if 'dynamodb' in record:
                applicationName = record['dynamodb']['NewImage']['ApplicationName']['S']
            else:
                applicationName = record['ApplicationName']
            protocols = dynamodbClient.Table('Application').query(
                ConsistentRead=True,
                KeyConditionExpression=Key('ApplicationName').eq(applicationName)
            )
            for item in protocols['Items']:
                if 'Protocol' in item:
                    item['Service'] = item['Protocol']
                else:
                    item['Protocol'] = item['Service']
                if item['Service'] == "lambda":
                    awslambda(item, t, defaults=config, G=G)
                if item['Service'] == "sqs":
                    sqs(item, G, defaults=config)
                if item['Service'] == "sns":
                    sns(item, G, defaults=config)
                if item['Service'] == "s3":
                    s3(item, G, defaults=config)
                if item['Service'] == "kms":
                    kms(item, G, defaults=config)
                if item['Service'] == "dynamodb":
                    dynamodb(item, G, defaults=config)
                if item['Service'] == "stepfunctions":
                    stepfunctions(item, G, defaults=config)
                if item['Protocol'] == "iam":
                    iamTemplate = Template()
                    iamTemplate.add_version("2010-09-09")
                    Giam = nx.DiGraph()
                    iam(item, Giam, defaults=config)
                    writeTemplate(iamTemplate, Giam)

            writeTemplate(t, G)
            template = StringIO(to_yaml(t.to_json(), clean_up=True))
            s3Client.put_object(
                Bucket=os.environ['CLOUDFORMATION_BUCKET'] if os.getenv('CLOUDFORMATION_BUCKET') else config.get(
                    'DEFAULT', 'CloudformationBucket'),
                Key=applicationName + "/" + applicationName + ".template",
                Body=template.read()
            )
            template.close()
            tmpName = str(uuid.uuid4())
            nx.nx_pydot.write_dot(G, "{}{}-{}.dot".format(config.get('DEFAULT', 'WriteFileDirectory'), tmpName,
                                                          applicationName))

            with open("{}{}-{}.dot".format(config.get('DEFAULT', 'WriteFileDirectory'), tmpName, applicationName),
                      "rb") as dotFile:
                s3Client.put_object(
                    Bucket=os.environ['CLOUDFORMATION_BUCKET'] if os.getenv('CLOUDFORMATION_BUCKET') else config.get(
                        'DEFAULT', 'CloudformationBucket'),
                    Key='{}/{}.dot'.format(applicationName, applicationName),
                    Body=dotFile.read()
                )

            template = StringIO(to_yaml(t.to_json(), clean_up=True))
            myzip = zipfile.ZipFile(config.get('DEFAULT', 'WriteFileDirectory') + applicationName + ".zip", 'w')
            myzip.writestr(applicationName + ".template", template.read())
            myzip.close()
            template.close()

            with open(config.get('DEFAULT', 'WriteFileDirectory') + applicationName + ".zip", "rb") as myzip:
                s3Client.put_object(
                    Bucket=os.environ['CLOUDFORMATION_BUCKET'] if os.getenv('CLOUDFORMATION_BUCKET') else config.get('DEFAULT', 'CloudformationBucket'),
                    Key=applicationName + "/" + applicationName + ".zip",
                    Body=myzip.read()
                )

            if iamTemplate is not None:
                template = StringIO(to_yaml(iamTemplate.to_json(), clean_up=True))
                s3Client.put_object(
                    Bucket=os.environ['CLOUDFORMATION_BUCKET'] if os.getenv('CLOUDFORMATION_BUCKET') else config.get(
                        'DEFAULT', 'CloudformationBucket'),
                    Key=applicationName + "/" + applicationName + "-IAM.template",
                    Body=template.read()
                )
                template.close()

                template = StringIO(to_yaml(iamTemplate.to_json(), clean_up=True))
                myzip = zipfile.ZipFile(config.get('DEFAULT', 'WriteFileDirectory') + applicationName + "-IAM.zip",
                                        'w')
                myzip.writestr(applicationName + "-IAM.template",
                               template.read())
                myzip.close()
                template.close()

                with open(config.get('DEFAULT', 'WriteFileDirectory') + applicationName + "-IAM.zip",
                          "rb") as myzip:
                    s3Client.put_object(
                        Bucket=os.environ['CLOUDFORMATION_BUCKET'] if os.getenv(
                            'CLOUDFORMATION_BUCKET') else config.get('DEFAULT', 'CloudformationBucket'),
                        Key=applicationName + "/" + applicationName + "-IAM.zip",
                        Body=myzip.read()
                    )
            retVal.append({
                'status': 'success',
                'applicationName': applicationName,
            })

        except Exception, e:
            print("Error: %s" % e)
            traceback.print_exc()
            retVal.append({
                'status': 'error',
                'applicationName': applicationName,
                'reason': traceback.format_exc(),
            })

    return retVal
