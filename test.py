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

applicationName = "RAIL"
protocols = dynamodbClient.Table('Application').query(
    KeyConditionExpression=Key('ApplicationName').eq(applicationName)
)
resources = {}
G = nx.DiGraph()

def dependsOn(node):
    retVal = []
    for u, v in G.edges_iter():
        if node == v:
            retVal.append(u.id)
    return retVal

def writeTemplate(template, graph):
    for node in graph.nodes_iter():
        depends = dependsOn(node)
        if depends != []:
            node.troposphereResource.__setattr__('DependsOn', dependsOn(node))
        template.add_resource(node.troposphereResource)

for item in protocols['Items']:
    if item['Protocol'] == "lambda":
        awslambda(item, t, defaults=config, G=G)
    if item['Protocol'] == "sqs":
        sqs(item, G, defaults=config)
    if item['Protocol'] == "sns":
        sns(item, G, defaults=config)
    if item['Protocol'] == 's3':
        s3(item, G, defaults=config)
    if item['Protocol'] == "kms":
        kms(item, G, defaults=config)
    if item['Protocol'] == "dynamodb":
        dynamodb(item, G, defaults=config)
    # if item['Protocol'] == "apigateway":
    #     t = apigateway(item, t, defaults=config)
    if item['Protocol'] == "iam":
        iamTemplate = Template()
        iamTemplate.add_version("2010-09-09")
        Giam = nx.DiGraph()
        iam(item, Giam, defaults=config)
        writeTemplate(iamTemplate, Giam)
        # print(to_yaml(iamTemplate.to_json(), clean_up=True))


# nx.draw(G,pos=nx.spring_layout(G))
# plt.show()


writeTemplate(t, G)

print(to_yaml(t.to_json(), clean_up=True))
