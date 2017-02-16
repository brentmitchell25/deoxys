from troposphere.sqs import Queue, RedrivePolicy
from troposphere import Ref, Join


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
                    queue['DelaySeconds']) if 'DelaySeconds' in queue else Ref('AWS::NoValue'),
                "RedrivePolicy": RedrivePolicy(
                    deadLetterTargetArn=Join("",
                                             ["arn:aws:sqs", ":", Ref("AWS::Region"), ":", Ref("AWS::AccountId"), ":",
                                              queue['DeadLetterQueue']['Name']]),
                    maxReceiveCount=int(queue['DeadLetterQueue']['MaxReceiveCount'] if 'MaxReceiveCount' in queue[
                        'DeadLetterQueue'] else
                                        defaults.get('DEFAULT', 'MaxReceiveCount'))
                ) if 'DeadLetterQueue' in queue else Ref('AWS::NoValue'),
                "VisibilityTimeout": str(
                    queue['VisibilityTimeout']) if 'VisibilityTimeout' in queue else Ref('AWS::NoValue'),
                "DependsOn": str(queue['DeadLetterQueue']['Name']).replace("_", "") + item[
                    'Protocol'] if "DeadLetterQueue" in queue else None
            }
            resource = Queue(
                queue['QueueName'].replace("_", "") + item['Protocol'],
                **dict((k, v) for k, v in parameters.iteritems() if v is not None)
            )
            template.add_resource(resource)
    return template
