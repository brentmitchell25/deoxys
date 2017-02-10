from troposphere.awslambda import Function, Code, Permission, VPCConfig, Environment
from troposphere.events import Rule, Target
from troposphere import FindInMap, GetAtt, Join, Output
from troposphere import Parameter, Ref, Template

def awslambda(item, template, defaults):
    if 'Functions' in item:
        for function in item['Functions']:
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
                    ZipFile=defaults.get('DEFAULT','Code')
                )
            resource = Function(
                function['FunctionName'].replace('_', '') + item['Protocol'],
                FunctionName=function['FunctionName'],
                Description=function['Description'] if 'Description' in function else Ref('AWS::NoValue'),
                Code=code,
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
                Runtime=function['Runtime'] if 'Runtime' in function else 'nodejs4.3',
                MemorySize=function['MemorySize'] if 'MemorySize' in function else '128',
                Timeout=str(function['Timeout']) if 'Timeout' in function else '3',
            )
            if 'Poller' in function:
                template.add_resource(Rule(
                    function['FunctionName'].replace('_', '') + 'Poller',
                    Name=function['FunctionName'].replace('_', '') + 'Poller',
                    Description=function['FunctionName'].replace('_', '') + " Poller",
                    ScheduleExpression="rate(" + str(function['Poller']['Rate']) + ")",
                    State="ENABLED",
                    Targets=[Target(
                        Arn=GetAtt(resource, "Arn"),
                        Id=function['FunctionName'].replace('_', '')
                    )],
                    DependsOn=[function['FunctionName'].replace('_', '') + item['Protocol']]
                ))
            template.add_resource(resource)
    return template