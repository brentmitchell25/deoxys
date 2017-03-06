from troposphere import FindInMap, GetAtt, Join, Output
from troposphere import Parameter, Ref, Template
from troposphere.awslambda import Function, Code, Permission, VPCConfig, Environment
from troposphere.sqs import Queue, QueuePolicy
from troposphere.sns import Topic, TopicPolicy, SubscriptionResource, Subscription
from awacs.aws import Policy, Statement, Principal, Action, Condition, ConditionElement
from awacs.aws import Allow, ArnEquals, AWSPrincipal, Condition
import re
import awacs.sqs as sqs
from AWSObject import AWSObject
import awacs.awslambda as awslambda

regex = re.compile('[^a-zA-Z0-9]')


def sns(item, G, defaults):
    if 'Topics' in item:
        for topic in item['Topics']:
            subscriptions = []
            topicId = regex.sub('', topic['TopicName']) + item['Protocol']
            if 'CreateTopic' not in topic:
                topic['CreateTopic'] = True

            if "Subscriptions" in topic:
                for subscription in topic["Subscriptions"]:
                    endpointId = regex.sub('', subscription["Endpoint"]) + regex.sub('', subscription["Protocol"])
                    if subscription["Protocol"] == "sqs":
                        endpoint = Join("", ["arn:aws:sqs:", Ref("AWS::Region"), ":", Ref("AWS::AccountId"),
                                             ":",
                                             subscription["Endpoint"]])
                    elif subscription["Protocol"] == "lambda":
                        endpoint = Join("",
                                        ["arn:aws:lambda:", Ref("AWS::Region"), ":", Ref("AWS::AccountId"),
                                         ":function:",
                                         subscription["Endpoint"]])
                    else:
                        endpoint = subscription["Endpoint"]

                    sub = Subscription(
                        Endpoint=endpoint,
                        Protocol=subscription["Protocol"]
                    )
                    subscriptions.append(sub)

                    if topic['CreateTopic'] == False:
                        subscriptionResourceId = regex.sub('', topic['TopicName']) + regex.sub('',
                                                                                               endpointId) + 'subscription'
                        subscriptionResource = SubscriptionResource(
                            subscriptionResourceId,
                            Endpoint=endpoint,
                            Protocol=subscription["Protocol"],
                            TopicArn=Join("",
                                          ["arn:aws:sns:", Ref("AWS::Region"), ":", Ref("AWS::AccountId"),
                                           ":",
                                           topic['TopicName']])
                        )
                        subscriptionResourceObj = AWSObject(subscriptionResourceId, subscriptionResource, subscription["Endpoint"] + "-Subscription")
                        G.add_node(subscriptionResourceObj)

                    if subscription["Protocol"] == "lambda":
                        permissionId = endpointId + regex.sub('', topic['TopicName']) + 'InvokePermission'
                        permission = Permission(
                            permissionId,
                            Action="lambda:InvokeFunction",
                            Principal="sns.amazonaws.com",
                            SourceArn=Join("",
                                           ["arn:aws:sns:", Ref("AWS::Region"), ":", Ref("AWS::AccountId"),
                                            ":",
                                            topic['TopicName']]),
                            FunctionName=subscription["Endpoint"]
                        )
                        permissionObj = AWSObject(permissionId, permission, "InvokeFunctionPermission")
                        G.add_node(permissionObj)
                        G.add_edge(permissionObj, AWSObject(regex.sub("",subscription["Endpoint"] + subscription["Protocol"])))
                        if str(topic['CreateTopic']) == 'true':
                            G.add_edge(permissionObj, AWSObject(topicId))
                    elif subscription["Protocol"] == "sqs":
                        queuePolicyId = regex.sub('', topic['TopicName']) + 'QueuePolicy'
                        queuePolicy = QueuePolicy(
                            queuePolicyId,
                            PolicyDocument=Policy(
                                Id=endpointId + topicId + 'Policy',
                                Version='2012-10-17',
                                Statement=[Statement(
                                    Effect="Allow",
                                    Action=[sqs.SendMessage],
                                    Principal=Principal("Service", ["sns.amazonaws.com"]),
                                    Resource=[endpoint],
                                    Condition=Condition(ArnEquals({
                                        "aws:SourceArn": [Join("", ["arn:aws:sns:", Ref("AWS::Region"), ":",
                                                                    Ref("AWS::AccountId"), ":",
                                                                    topic['TopicName']])]
                                    }))
                                )],
                            ),
                            Queues=[
                                Join("", ["https://sqs.", Ref("AWS::Region"), ".amazonaws.com/",
                                          Ref("AWS::AccountId"), "/",
                                          subscription["Endpoint"]])]
                        )

                        queuePolObj = AWSObject(queuePolicyId, queuePolicy, "QueuePolicy")
                        G.add_node(queuePolObj)
                        G.add_edge(queuePolObj, AWSObject(regex.sub("",subscription["Endpoint"] + subscription["Protocol"])))
                        if str(topic['CreateTopic']) == 'true':
                            G.add_edge(queuePolicy, AWSObject(topicId))

            if topic['CreateTopic'] == True:
                resource = Topic(
                    topicId,
                    TopicName=topic['TopicName'],
                    Subscription=subscriptions,
                )
                topicObj = AWSObject(topicId, resource, topicId)
                if G.has_node(topicObj):
                    for node in G.nodes():
                        if str(node) == topicId:
                            node.troposphereResource = resource
                            break
                else:
                    G.add_node(topicObj)
