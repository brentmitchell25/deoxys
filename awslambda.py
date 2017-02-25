from troposphere.awslambda import Function, Code, Permission, VPCConfig, Environment
from troposphere.events import Rule, Target
from troposphere.apigateway import RestApi, Resource, Method, Integration, Deployment, IntegrationResponse, \
    MethodResponse
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
            SecurityGroupIds=(defaults.get('DEFAULT', 'LambdaSecurityGroupIds')).split(','),
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

            if 'Api' in function:
                parameters = {
                    'ApiName': function['Api']['ApiName'],
                    'Path': function['Api']['Path'],
                    'HttpMethod': function['Api']['HttpMethod'],
                    'Asynchronous': function['Api']['Asynchronous'] if 'Asynchronous' in function['Api'] else None,
                    'Role': function['Api']['Role'],
                    'AuthorizationType': function['Api']['AuthorizationType'] if 'AuthorizationType' in function[
                        'Api'] else None,
                    'Uri': function['Api']['Uri'],
                    'StageName': function['Api']['StageName'],
                    'RequestParameters': function['Api']['RequestParameters'] if 'RequestParameters' in function[
                        'Api'] else None,
                    'IntegrationRequestTemplates': function['Api'][
                        'IntegrationRequestTemplates'] if 'IntegrationRequestTemplates' in function[
                        'Api'] else None,
                }

                restApi = RestApi(
                    regex.sub("", parameters['ApiName']) + 'api',
                    Name=parameters["ApiName"],
                )
                apiResource = Resource(
                    regex.sub("", parameters['Path']) + 'Path',
                    RestApiId=Ref(restApi),
                    ParentId=GetAtt(restApi, "RootResourceId"),
                    PathPart=str(parameters['Path']).replace("/", ""),
                    DependsOn=regex.sub("", parameters['ApiName']) + 'api'
                )

                methodParameters = {}
                if str(parameters['Asynchronous']).lower() == 'true':
                    methodParameters = {
                        "RestApiId": Ref(restApi),
                        "ResourceId": Ref(apiResource),
                        "HttpMethod": str(parameters['HttpMethod']).upper(),
                        "AuthorizationType": parameters['AuthorizationType'],
                        "Integration": Integration(
                            Type="AWS",
                            Credentials=Join("", ["arn:aws:iam::", Ref("AWS::AccountId"), ":", "role/",
                                                  parameters['Role']]),
                            IntegrationHttpMethod=str(parameters['HttpMethod']).upper(),
                            Uri=Join("", ["arn:aws:apigateway:us-east-1:lambda:path/", parameters['Uri']]),
                            IntegrationResponses=[
                                IntegrationResponse(
                                    StatusCode='200'
                                )
                            ],
                            RequestParameters={
                                "integration.request.header.X-Amz-Invocation-Type": '\'Event\''
                            }
                        ),
                        "MethodResponses": [
                            MethodResponse(
                                StatusCode='200'
                            )
                        ],
                        "DependsOn": regex.sub("", parameters['Path']) + 'Path'
                    }
                else:
                    methodParameters = {
                        "RestApiId": Ref(restApi),
                        "ResourceId": Ref(apiResource),
                        "HttpMethod": str(parameters['HttpMethod']).upper(),
                        "AuthorizationType": parameters['AuthorizationType'],
                        "Integration": Integration(
                            Type="AWS",
                            IntegrationHttpMethod=str(parameters['HttpMethod']).upper(),
                            Uri=Join("", ["arn:aws:apigateway:us-east-1:lambda:path/", parameters['Uri']]),
                            IntegrationResponses=[
                                IntegrationResponse(
                                    StatusCode='200'
                                )
                            ],
                        ),
                        "RequestParameters": parameters['RequestParameters'],
                        "RequestTemplates": parameters['RequestParameters'],
                        "MethodResponses": [
                            MethodResponse(
                                StatusCode='200'
                            )
                        ],
                        "DependsOn": regex.sub("", parameters['Path']) + 'Path'
                    }

                method = Method(
                    regex.sub("", parameters['HttpMethod']) + 'Method',
                    **dict((k, v) for k, v in methodParameters.iteritems() if v is not None)
                )

                deployment = Deployment(
                    regex.sub("", parameters['ApiName']) + 'Deployment',
                    RestApiId=Ref(restApi),
                    StageName=parameters['StageName'],
                    DependsOn=regex.sub("", parameters['HttpMethod']) + 'Method',
                )
                template.add_resource(restApi)
                template.add_resource(apiResource)
                template.add_resource(method)
                template.add_resource(deployment)

                template.add_resource(Permission(
                    regex.sub("", parameters['Path']) + 'Path' + 'Permission',
                    Action="lambda:InvokeFunction",
                    Principal="apigateway.amazonaws.com",
                    SourceArn=Join("", ["arn:aws:execute-api:", Ref("AWS::Region"), ":", Ref("AWS::AccountId"), ":",
                                        Ref(restApi), "/*/", parameters['HttpMethod'], "/",
                                        str(parameters['Path']).replace("/", "")]),
                    FunctionName=Ref(resource),
                    DependsOn=regex.sub("", parameters['ApiName']) + 'Deployment'
                ))

                template.add_resource(Permission(
                    regex.sub("", parameters['Path']) + 'Paths' + 'Permission',
                    Action="lambda:InvokeFunction",
                    Principal="apigateway.amazonaws.com",
                    SourceArn=Join("", ["arn:aws:execute-api:", Ref("AWS::Region"), ":", Ref("AWS::AccountId"), ":",
                                        Ref(restApi), "/*/", parameters['HttpMethod'], "/",
                                        str(parameters['Path']).replace("/", "")]),
                    FunctionName="RAILBourqueExport",
                    DependsOn=regex.sub("", parameters['ApiName']) + 'Deployment'
                ))
    return template
