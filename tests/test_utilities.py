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
import glob, os
import json
regex = re.compile('[^a-zA-Z0-9]')


def mapTestJsonFiles(inputDirectoryName, directory='test_input'):
    retVal = {
        'Items': []
    }
    fileName = '{}/{}/*.json'.format(directory, inputDirectoryName)
    # if len(glob.glob(fileName)) == 0:
    #     os.write(fileName, )
    #     return None
    for file in glob.glob(fileName):
        with open(file) as data_file:
            retVal['Items'].append(json.load(data_file))
    return retVal

def mapJsonToYml(jsonInput):
    return runTest(jsonInput)

def testYaml(testYaml, inputDirectoryName, directory='test_output'):
    fileName = '{}/{}.yml'.format(directory, inputDirectoryName)
    if not os.path.isfile(fileName):
        with open(fileName, "w") as text_file:
            text_file.write(testYaml)
            retVal = testYaml
    else:
        with open(fileName, "r") as text_file:
            retVal = text_file.read()
    return retVal


def getImmediateSubdirectories(a_dir):
    return [name for name in os.listdir(a_dir)
            if os.path.isdir(os.path.join(a_dir, name))]

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
        template.add_resource(graph.node[node]['resource'])

def runTest(services, runWIthDefaultConfig=False):
    config = ConfigParser.RawConfigParser()
    if os.path.exists("../defaults.ini") and runWIthDefaultConfig:
        config.read('../defaults.ini')
    else:
        config.read('../default.ini')

    t = Template()
    t.add_version("2010-09-09")

    G = nx.DiGraph()
    retVal = {}
    for item in services['Items']:
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
        if item['Service'] == "iam":
            iamTemplate = Template()
            iamTemplate.add_version("2010-09-09")
            Giam = nx.DiGraph()
            iam(item, Giam, defaults=config)
            writeTemplate(iamTemplate, Giam)
            retVal['iam'] = to_yaml(iamTemplate.to_json(), clean_up=True)

    writeTemplate(t, G)

    retVal['services'] = to_yaml(t.to_json(), clean_up=True)
    return retVal
