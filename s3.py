from troposphere.s3 import Bucket, Tags
import re

regex = re.compile('[^a-zA-Z]')


def s3(item, template, defaults):
    if 'Buckets' in item:
        for bucket in item['Buckets']:
            parameters = {
                "BucketName": bucket['BucketName'],
                "DeletionPolicy": bucket['DeletionPolicy'] if 'DeletionPolicy' in item else 'Retain'
            }

            template.add_resource(Bucket(
                regex.sub("", bucket['BucketName']) + 'bucket',
                **dict((k, v) for k, v in parameters.iteritems() if v is not None)
            ))
    return template
