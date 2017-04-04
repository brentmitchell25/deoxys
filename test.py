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

applicationName = "ASH-INVTXN-dev"
protocols = dynamodbClient.Table('Application').query(
    KeyConditionExpression=Key('ApplicationName').eq(applicationName)
)
resources = {}

def dependsOn(node, graph):
    retVal = []
    for u, v in graph.edges_iter():
        if node == u:
            retVal.append(regex.sub("", v))
    return retVal

def writeTemplate(template, graph):
    for node in graph:
        depends = dependsOn(node, graph)
        if depends != []:
            graph.node[node]['resource'].__setattr__('DependsOn', dependsOn(node, graph=graph))
        template.add_resource(graph.node[node]['resource'])

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
d = []
for node in G:
    # G.node
    d.append(str(node))
# pos=nx.nx_pydot.graphviz_layout(G,prog='fdp')
# nx.draw(G,pos, with_labels=True, font_size=8)
    # G = nx.complete_graph(4)
    #
    # G.node[0]['image'] = img
    # G.node[1]['image'] = img
    # G.node[2]['image'] = img
    # G.node[3]['image'] = img


# pos=nx.spring_layout(G)
# nx.draw(G,pos)

# add images on edges
# ax=plt.gca()
# fig=plt.gcf()
# label_pos = 0.5 # middle of edge, halfway between nodes
# trans = ax.transData.transform
# trans2 = fig.transFigure.inverted().transform
# imsize = 0.1 # this is the image size
# for (n1,n2) in G.edges():
#     (x1,y1) = pos[n1]
#     (x2,y2) = pos[n2]
#     (x,y) = (x1 * label_pos + x2 * (1.0 - label_pos),
#              y1 * label_pos + y2 * (1.0 - label_pos))
#     xx,yy = trans((x,y)) # figure coordinates
#     xa,ya = trans2((xx,yy)) # axes coordinates
#     imsize = 0.05
#     img =  G[n1][n2]['image']
#     a = plt.axes([xa-imsize/2.0,ya-imsize/2.0, imsize, imsize ])
#     a.imshow(img)
#     a.set_aspect('equal')
#     a.axis('off')

# nx.draw(G,pos=nx.spring_layout(G,), with_labels=True, font_size=8)

# for node in G.nodes():
    # print node

# plt.show()
print('HERE')
nx.nx_pydot.write_dot(G, 'test.dot')
# pos = nx.nx_pydot.graphviz_layout(G)
pos=nx.nx_pydot.graphviz_layout(G,prog='dot')
print('HERE')
nx.draw(G,pos,  font_size=8,  with_labels=True)
plt.show()
writeTemplate(t, G)

print(to_yaml(t.to_json(), clean_up=True))
