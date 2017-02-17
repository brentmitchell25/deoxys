from troposphere.awslambda import Function, Code, Permission, VPCConfig, Environment
from troposphere.events import Rule, Target
from troposphere import FindInMap, GetAtt, Join, Output
from troposphere import Parameter, Ref, Template
import awacs.awslambda as awslambda
from awacs.aws import Action, Principal
import re
regex = re.compile('[^a-zA-Z]')

def getCode(function, defaults):
    code = None
    if 'Code' in function and 'S3Bucket' in function['Code'] and 'S3Key' in function['Code']:
        code = Code(
            S3Bucket=function['Code']['S3Bucket'],
            S3Key=function['Code']['S3Key']
        )
    elif 'Code' in function and 'ZipFile' in function['Code']:
        code = Code(
            ZipFile=function['Code']['ZipFile']
        )
    else:
        code = Code(
            ZipFile=defaults.get('DEFAULT', 'Code')
        )
    return code

def getVpcConfig(function, defaults):
    code = None
    if 'VpcConfig' in function:
        code = Code(
            S3Bucket=function['Code']['S3Bucket'],
            S3Key=function['Code']['S3Key']
        )
    elif 'Code' in function and 'ZipFile' in function['Code']:
        code = Code(
            ZipFile=function['Code']['ZipFile']
        )
    else:
        code = Code(
            ZipFile=defaults.get('DEFAULT', 'Code')
        )
    return code

def awslambda(item, template, defaults):
    if 'Functions' in item:
        for function in item['Functions']:
            functionId = regex.sub("",function['FunctionName'])
            resource = Function(
                functionId + item['Protocol'],
                FunctionName=function['FunctionName'],
                Description=function['Description'] if 'Description' in function else Ref('AWS::NoValue'),
                Code=function,
                Handler=function['Handler'] if 'Handler' in function else 'index.handler',
                Environment=Environment(
                    Variables={key: value for key, value in
                               list(function["Environment"]["Variables"].items())}
                ) if 'Environment' in function else Ref('AWS::NoValue'),
                VpcConfig=VPCConfig(
                    SecurityGroupIds=[function['VpcConfig']['SecurityGroupIds']],
                    SubnetIds=function['VpcConfig']['SubnetIds'].split(',')
                ) if 'VpcConfig' in function else Ref('AWS::NoValue'),
                Role=Join("", ["arn:aws:iam::", Ref("AWS::AccountId"), ":role/",
                               function['Role']]),
                Runtime=function['Runtime'] if 'Runtime' in function else defaults.get("DEFAULT", "LambdaRuntime"),
                MemorySize=function['MemorySize'] if 'MemorySize' in function else defaults.get("DEFAULT", "LambdaMemorySize"),
                Timeout=str(function['Timeout']) if 'Timeout' in function else defaults.get("DEFAULT", "Timeout"),
            )
            if 'Poller' in function:
                pollerId = functionId + 'Poller'
                poller = template.add_resource(Rule(
                    pollerId,
                    Name=function['FunctionName'] + 'Poller',
                    Description=function['FunctionName'] + " Poller",
                    ScheduleExpression="rate(" + str(function['Poller']['Rate']) + ")",
                    State="ENABLED",
                    Targets=[Target(
                        Arn=GetAtt(resource, "Arn"),
                        Id=functionId
                    )],
                    DependsOn=[functionId + item['Protocol']]
                ))
                template.add_resource(Permission(
                    pollerId + 'Permission',
                    Action=awslambda.InvokeFunction,
                    Principal=Principal("Service", ["events.amazonaws.com"]),
                    SourceArn=GetAtt(poller, "Arn"),
                    FunctionName=Ref(resource)
                ))
            template.add_resource(resource)
    return template