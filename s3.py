from troposphere.s3 import Bucket, Tags

def s3(item, template, defaults):
    if 'Buckets' in item:
        for bucket in item['Buckets']:
            template.add_resource(Bucket(
                bucket['BucketName'].replace("-", "") + 'bucket',
                BucketName=bucket['BucketName'],
                DeletionPolicy=bucket['DeletionPolicy'] if 'DeletionPolicy' in item else 'Retain'
            ))
    return template
