from troposphere.sqs import Queue, RedrivePolicy
from troposphere import Ref, Join
import re

regex = re.compile('[^a-zA-Z]')


def sqs(item, template, defaults):
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
                "DependsOn": str(queue['DeadLetterQueue']['Name']).replace("_", "") + item[
                    'Protocol'] if "DeadLetterQueue" in queue else None
            }
            resource = Queue(
                regex.sub('', queue['QueueName']) + item['Protocol'],
                **dict((k, v) for k, v in parameters.iteritems() if v is not None)
            )
            template.add_resource(resource)
    return template
