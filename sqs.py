from troposphere.sqs import Queue, QueuePolicy


def sqs(item, template, defaults):
    if 'Queues' in item:
        for queue in item['Queues']:
            resource = Queue(
                queue['QueueName'].replace("_", "") + item['Protocol'],
                QueueName=queue['QueueName'],
                ReceiveMessageWaitTimeSeconds=str(
                    queue['ReceiveMessageWaitTimeSeconds']) if 'ReceiveMessageWaitTimeSeconds' in queue else defaults[
                    'ReceiveMessageWaitTimeSeconds'],
                MessageRetentionPeriod=str(
                    queue[
                        'MessageRetentionPeriod']) if 'MessageRetentionPeriod' in queue else defaults[
                    'MessageRetentionPeriod'],
            )
            template.add_resource(resource)
    return template
