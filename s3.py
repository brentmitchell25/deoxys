from troposphere.s3 import Bucket, Tags
import re
from AWSObject import AWSObject
regex = re.compile('[^a-zA-Z]')


def s3(item, G, defaults):
    if 'Buckets' in item:
        for bucket in item['Buckets']:
            parameters = {
                "BucketName": bucket['BucketName'],
                "DeletionPolicy": bucket['DeletionPolicy'] if 'DeletionPolicy' in item else 'Retain'
            }

            bucketId = regex.sub("", bucket['BucketName']) + 'bucket'
            bucket = Bucket(
                bucketId,
                **dict((k, v) for k, v in parameters.iteritems() if v is not None)
            )

            bucketObj = AWSObject(bucketId, bucket)
            G.add_node(bucketObj)
