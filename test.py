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
import re
import networkx as nx
import matplotlib.pyplot as plt
import os
import zipfile
regex = re.compile('[^a-zA-Z0-9]')

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

applicationName = "ASH-FXRATE-uat"
protocols = dynamodbClient.Table('Application').query(
    KeyConditionExpression=Key('ApplicationName').eq(applicationName)
)
resources = {}

def dependsOn(node, graph):
    retVal = []
    for u, v in G.edges_iter():
        if node == u:
            retVal.append(regex.sub("", v.id))
    return retVal

def writeTemplate(template, graph):
    for node in graph.nodes_iter():
        depends = dependsOn(node, graph)
        if depends != []:
            node.troposphereResource.__setattr__('DependsOn', dependsOn(node, graph=graph))
        template.add_resource(node.troposphereResource)

G = nx.DiGraph()

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

# pos=nx.nx_pydot.graphviz_layout(G,prog='fdp')
# nx.draw(G,pos, with_labels=True, font_size=8)


# nx.draw(G,pos=nx.spring_layout(G, scale=100), with_labels=True, font_size=8)

# for node in G.nodes():
    # print node

plt.show()
writeTemplate(t, G)
print(to_yaml(t.to_json(), clean_up=True))
