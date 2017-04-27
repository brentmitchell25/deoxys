import boto3
from boto3.dynamodb.conditions import Key
from test_utilities import runTest

dynamodbClient = boto3.resource('dynamodb')
s3Client = boto3.client('s3')

applicationName = "EBS-PRICECURVE-dev"
services = dynamodbClient.Table('Application').query(
    KeyConditionExpression=Key('ApplicationName').eq(applicationName)
)

retVal = runTest(services, runWIthDefaultConfig=True)
if 'iam' in retVal:
    print(retVal['iam'])
if 'services' in retVal:
    print(retVal['services'])