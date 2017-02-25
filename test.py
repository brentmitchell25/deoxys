from awslambda import awslambda
from sqs import sqs
from sns import sns
from s3 import s3
from kms import kms
from iam import iam
from apigateway import apigateway
from dynamodb import dynamodb
from troposphere import Template
from cfn_flip import flip, to_yaml
from boto3.dynamodb.conditions import Key
from cStringIO import StringIO
import ConfigParser
import boto3
import yaml
import json
import sys
import networkx as nx
import matplotlib.pyplot as plt
import os
import zipfile

# Environment Variables

config = ConfigParser.RawConfigParser()
if os.path.exists("defaults.ini"):
    config.read('defaults.ini')
else:
    config.read('default.ini')

dynamodbClient = boto3.resource('dynamodb')
s3Client = boto3.client('s3')

t = Template()
t.add_version("2010-09-09")

applicationName = "Test"
protocols = dynamodbClient.Table('Application').query(
    KeyConditionExpression=Key('ApplicationName').eq(applicationName)
)
resources = {}
G = nx.DiGraph()

def dependsOn(node):
    retVal = []
    for u, v in G.edges_iter():
        if node == u:
            retVal.append(v.id)
    return retVal

def writeTemplate(template, graph):
    for node in graph.nodes_iter():
        depends = dependsOn(node)
        if depends != []:
            node.troposphereResource.__setattr__('DependsOn', dependsOn(node))
        template.add_resource(node.troposphereResource)

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
    # if item['Protocol'] == "apigateway" or item['Service'] == "apigateway":
    #     t = apigateway(item, t, defaults=config)
    if item['Service'] == "iam":
        iamTemplate = Template()
        iamTemplate.add_version("2010-09-09")
        Giam = nx.DiGraph()
        iam(item, Giam, defaults=config)
        writeTemplate(iamTemplate, Giam)
        # print(to_yaml(iamTemplate.to_json(), clean_up=True))


nx.draw(G, with_labels=True)
plt.show()


writeTemplate(t, G)

print(to_yaml(t.to_json(), clean_up=True))
