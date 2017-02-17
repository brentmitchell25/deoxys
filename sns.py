from troposphere import FindInMap, GetAtt, Join, Output
from troposphere import Parameter, Ref, Template
from troposphere.awslambda import Function, Code, Permission, VPCConfig, Environment
from troposphere.sqs import Queue, QueuePolicy
from troposphere.sns import Topic, TopicPolicy, SubscriptionResource, Subscription
from awacs.aws import Policy, Statement, Principal, Action, Condition, ConditionElement
from awacs.aws import Allow, ArnEquals, AWSPrincipal, Condition
import re
import awacs.sqs as sqs
import awacs.awslambda as awslambda

regex = re.compile('[^a-zA-Z]')


def sns(item, template, defaults):
    if 'Topics' in item:
        for topic in item['Topics']:
            subscriptions = []
            dependsOn = []
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
                    dependsOn.append(subscription["Endpoint"] + subscription["Protocol"])
                    subscriptions.append(sub)

                    if topic['CreateTopic'] == False:
                        template.add_resource(SubscriptionResource(
                            regex.sub('', topic['TopicName']) + regex.sub('', endpointId) + 'subscription',
                            Endpoint=endpoint,
                            Protocol=subscription["Protocol"],
                            TopicArn=Join("",
                                          ["arn:aws:sns:", Ref("AWS::Region"), ":", Ref("AWS::AccountId"),
                                           ":",
                                           topic['TopicName']])
                        ))
                    if subscription["Protocol"] == "lambda":
                        template.add_resource(Permission(
                            endpointId + regex.sub('', topic['TopicName']) + 'InvokePermission',
                            DependsOn=[topicId, endpointId] if topic['CreateTopic'] == True else [
                                endpointId],
                            Action="lambda:InvokeFunction",
                            Principal="sns.amazonaws.com",
                            SourceArn=Join("",
                                           ["arn:aws:sns:", Ref("AWS::Region"), ":", Ref("AWS::AccountId"),
                                            ":",
                                            topic['TopicName']]),
                            FunctionName=subscription["Endpoint"]
                        ))
                    elif subscription["Protocol"] == "sqs":
                        template.add_resource(QueuePolicy(
                            regex.sub('', topic['TopicName']) + 'QueuePolicy',
                            DependsOn=[topicId, endpointId] if topic['CreateTopic'] == True else [
                                endpointId],
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
                        ))

            if topic['CreateTopic'] == True:
                resource = Topic(
                    topicId,
                    TopicName=topic['TopicName'],
                    Subscription=subscriptions,
                )
                template.add_resource(resource)
    return template
