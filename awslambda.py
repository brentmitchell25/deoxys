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
    vpcConfig = None
    if 'VpcConfig' in function and str(function['VpcConfig']).lower().strip() == "true":
        vpcConfig = VPCConfig(
            SecurityGroupIds=(defaults.get('DEFAULT', 'LambdaSecuritGroupIds')).split(','),
            SubnetIds=(defaults.get('DEFAULT', 'LambdaSubnetIds')).split(',')
        )
    elif 'VpcConfig' in function :
        vpcConfig = VPCConfig(
            SecurityGroupIds=function['VpcConfig']['SecurityGroupIds'].split(','),
            SubnetIds=function['VpcConfig']['SubnetIds'].split(',')
        )
    return vpcConfig


def awslambda(item, template, defaults):
    if 'Functions' in item:
        for function in item['Functions']:
            functionId = regex.sub("", function['FunctionName'])
            parameters = {
                "FunctionName": function['FunctionName'],
                "Description": function['Description'] if 'Description' in function else None,
                "Code": getCode(function, defaults=defaults),
                "Handler": function[
                    'Handler'] if 'Handler' in function else 'index.handler',
                "Environment": Environment(
                    Variables={key: value for key, value in
                               list(function["Environment"]["Variables"].items())}
                ) if 'Environment' in function else None,
                "VpcConfig": getVpcConfig(function, defaults=defaults),
                "Role": Join("",
                             ["arn:aws:iam::",
                              Ref(
                                  "AWS::AccountId"),
                              ":role/",
                              function['Role']]),
                "Runtime": function[
                    'Runtime'] if 'Runtime' in function else defaults.get(
                    "DEFAULT", "LambdaRuntime"),
                "MemorySize":
                    function['MemorySize'] if 'MemorySize' in function else defaults.get("DEFAULT", "LambdaMemorySize"),
                "Timeout": str(function['Timeout']) if 'Timeout' in function else defaults.get("DEFAULT", "Timeout")
            }
            resource = Function(
                functionId + item['Protocol'],
                **dict((k, v) for k, v in parameters.iteritems() if v is not None)
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
                    Action="lambda:InvokeFunction",
                    Principal="events.amazonaws.com",
                    SourceArn=GetAtt(poller, "Arn"),
                    FunctionName=Ref(resource)
                ))
            template.add_resource(resource)
    return template
