from troposphere.apigateway import ApiKey
import re

regex = re.compile('[^a-zA-Z]')


def apigateway(item, template, defaults):
    if 'Endpoints' in item:
        for endpoint in item['Buckets']:
            parameters = {
                "Path": endpoint['Path'],
            }

            template.add_resource(Bucket(
                regex.sub("", bucket['BucketName']) + 'bucket',
                **dict((k, v) for k, v in parameters.iteritems() if v is not None)
            ))
    return template
