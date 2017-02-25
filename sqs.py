from troposphere.sqs import Queue, RedrivePolicy
from troposphere import Ref, Join
from AWSObject import AWSObject
import re

regex = re.compile('[^a-zA-Z0-9]')


def sqs(item, G, defaults):
    if 'Queues' in item:
        for queue in item['Queues']:
            parameters = {
                "QueueName": queue['QueueName'],
                "ReceiveMessageWaitTimeSeconds": str(
                    queue[
                        'ReceiveMessageWaitTimeSeconds']) if 'ReceiveMessageWaitTimeSeconds' in queue else defaults.get(
                    'DEFAULT',
                    'ReceiveMessageWaitTimeSeconds'),
                "MessageRetentionPeriod": str(
                    queue[
                        'MessageRetentionPeriod']) if 'MessageRetentionPeriod' in queue else defaults.get('DEFAULT',
                                                                                                          'MessageRetentionPeriod'),
                "DelaySeconds": str(
                    queue['DelaySeconds']) if 'DelaySeconds' in queue else None,
                "RedrivePolicy": RedrivePolicy(
                    deadLetterTargetArn=Join("",
                                             ["arn:aws:sqs", ":", Ref("AWS::Region"), ":", Ref("AWS::AccountId"), ":",
                                              queue['DeadLetterQueue']['Name']]),
                    maxReceiveCount=int(queue['DeadLetterQueue']['MaxReceiveCount'] if 'MaxReceiveCount' in queue[
                        'DeadLetterQueue'] else
                                        defaults.get('DEFAULT', 'MaxReceiveCount'))
                ) if 'DeadLetterQueue' in queue else None,
                "VisibilityTimeout": str(
                    queue['VisibilityTimeout']) if 'VisibilityTimeout' in queue else None,
            }
            queueId = regex.sub('', queue['QueueName']) + item['Protocol']
            resource = Queue(
                queueId,
                **dict((k, v) for k, v in parameters.iteritems() if v is not None)
            )
            G.add_node(AWSObject(queueId, resource, queue['QueueName']))
    return G
