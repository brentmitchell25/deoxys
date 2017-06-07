from troposphere import FindInMap, GetAtt, Join, Output
from troposphere import Parameter, Ref, Template
from troposphere.awslambda import Function, Code, Permission, VPCConfig, Environment
from troposphere.sqs import Queue, QueuePolicy
from troposphere.sns import Topic, TopicPolicy, SubscriptionResource, Subscription
from awacs.aws import Policy, Statement, Principal, Action, Condition, ConditionElement
from awacs.aws import Allow, ArnEquals, AWSPrincipal, Condition
import re
import utilities
import awacs.sqs as sqs
import awacs.awslambda as awslambda
import matplotlib.image as mpimg

lambdaImg = './AWS_Simple_Icons/Compute/Compute_AWSLambda.png'
snsImg = './AWS_Simple_Icons/Messaging/Messaging_AmazonSNS_topic.png'
sqsImg = './AWS_Simple_Icons/Messaging/Messaging_AmazonSQS_queue.png'

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
                        utilities.mergeNode(G, id=subscriptionResourceId, resource=subscriptionResource, image=snsImg,
                                            name=subscription["Endpoint"] + "-Subscription")

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
                        utilities.mergeNode(G, id=permissionId, resource=permission, image=lambdaImg,
                                            name="InvokeFunctionPermission")

                        G.add_edge(permissionId, regex.sub("", subscription["Endpoint"] + subscription["Protocol"]))
                        if str(topic['CreateTopic']) == 'true':
                            G.add_edge(permissionId, topicId)
                    elif subscription["Protocol"] == "sqs":
                        queuePolicyId = endpointId + 'QueuePolicy'
                        statement = Statement(
                            Effect="Allow",
                            Action=[sqs.SendMessage],
                            Principal=Principal('*'),
                            Resource=[endpoint],
                            Condition=Condition(ArnEquals({
                                "aws:SourceArn": [Join("", ["arn:aws:sns:", Ref("AWS::Region"), ":",
                                                            Ref("AWS::AccountId"), ":",
                                                            topic['TopicName']])]
                            }))
                        )
                        # Need to check if multiple topics are subscribed to the same queue
                        if G.has_node(queuePolicyId):
                            G.node[queuePolicyId]['resource'].__dict__['resource']['Properties']['PolicyDocument'].__dict__['resource']['Statement'].append(statement)
                        else:
                            queuePolicy = QueuePolicy(
                                queuePolicyId,
                                PolicyDocument=Policy(
                                    Id=endpointId + topicId + 'Policy',
                                    Version='2012-10-17',
                                    Statement=[statement],
                                ),
                                Queues=[
                                    Join("", ["https://sqs.", Ref("AWS::Region"), ".amazonaws.com/",
                                              Ref("AWS::AccountId"), "/",
                                              subscription["Endpoint"]])]
                            )
                            utilities.mergeNode(G, id=queuePolicyId, resource=queuePolicy, image=sqsImg,
                                                name="QueuePolicy")
                        G.add_edge(queuePolicyId, regex.sub("", subscription["Endpoint"] + subscription["Protocol"]))
                        if str(topic['CreateTopic']) == 'true':
                            G.add_edge(queuePolicyId, topicId)

            if topic['CreateTopic'] == True:
                resource = Topic(
                    topicId,
                    TopicName=topic['TopicName'],
                    Subscription=subscriptions,
                )
                utilities.mergeNode(G, id=topicId, resource=resource, image=snsImg,
                                    name=topicId)
