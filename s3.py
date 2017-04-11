from troposphere.s3 import Bucket, Tags
import utilities
import re

import matplotlib.image as mpimg

s3Img = './AWS_Simple_Icons/Storage/Storage_AmazonS3_bucket.png'

regex = re.compile('[^a-zA-Z0-9]')


def s3(item, G, defaults):
    if 'Buckets' in item:
        for bucket in item['Buckets']:
            parameters = {
                "BucketName": bucket['BucketName'],
                "DeletionPolicy": bucket['DeletionPolicy'] if 'DeletionPolicy' in item else 'Retain'
            }

            bucketId = regex.sub("", bucket['BucketName']) + 'bucket'
            bucketRes = Bucket(
                bucketId,
                **dict((k, v) for k, v in parameters.iteritems() if v is not None)
            )
            utilities.mergeNode(G, id=bucketId, resource=bucketRes, image=s3Img,
                                name=bucket['BucketName'])
