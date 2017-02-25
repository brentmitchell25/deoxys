from troposphere.awslambda import Function, Code, Permission, VPCConfig, Environment
from troposphere.apigateway import RestApi, Resource, Method, Integration, Deployment, IntegrationResponse, \
    MethodResponse
from AWSObject import AWSObject
from troposphere.events import Rule, Target
from troposphere import FindInMap, GetAtt, Join, Output
from troposphere import Parameter, Ref, Template
import re

regex = re.compile('[^a-zA-Z0-9]')


def getCode(function, defaults):
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
    elif 'VpcConfig' in function:
        vpcConfig = VPCConfig(
            SecurityGroupIds=function['VpcConfig']['SecurityGroupIds'].split(','),
            SubnetIds=function['VpcConfig']['SubnetIds'].split(',')
        )
    return vpcConfig


def awslambda(item, template, defaults, G):
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
            func = Function(
                functionId + item['Protocol'],
                **dict((k, v) for k, v in parameters.iteritems() if v is not None)
            )
            funcObj = AWSObject( functionId + item['Protocol'], func)
            G.add_node(funcObj)

            if 'Poller' in function:
                pollerId = functionId + 'Poller'
                permissionId = pollerId + 'Permission'
                poller = Rule(
                    pollerId,
                    Name=function['FunctionName'] + 'Poller',
                    Description=function['FunctionName'] + " Poller",
                    ScheduleExpression="rate(" + str(function['Poller']['Rate']) + ")",
                    State="ENABLED",
                    Targets=[Target(
                        Arn=GetAtt(func, "Arn"),
                        Id=functionId
                    )],
                )
                permission = Permission(
                    permissionId,
                    Action="lambda:InvokeFunction",
                    Principal="events.amazonaws.com",
                    SourceArn=GetAtt(poller, "Arn"),
                    FunctionName=Ref(func)
                )
                poll = AWSObject(pollerId,poller)
                perm = AWSObject(permissionId, permission)
                G.add_node(poll)
                G.add_node(perm)
                G.add_edge(poll, funcObj)
                G.add_edge(perm, funcObj)
                G.add_edge(perm, poll)
            if 'Api' in function:
                if str(function['Api']['Path']).startswith('/'):
                    function['Api']['Path'] = str(function['Api']['Path'])[1:]
                if str(function['Api']['Path']).endswith('/'):
                    function['Api']['Path'] = str(function['Api']['Path'])[:-1]
                parameters = {
                    'ApiName': function['Api']['ApiName'],
                    'Path': function['Api']['Path'],
                    'HttpMethod': function['Api']['HttpMethod'],
                    'Asynchronous': function['Api']['Asynchronous'] if 'Asynchronous' in function['Api'] else 'false',
                    'Role': function['Api']['Role'] if 'Role' in function['Api'] else None,
                    'AuthorizationType': function['Api']['AuthorizationType'] if 'AuthorizationType' in function[
                        'Api'] else defaults.get('DEFAULT', 'AuthorizationType'),
                    'Uri': function['Api']['Uri'] if 'Uri' in function['Api'] else None,
                    'StageName': function['Api']['StageName'],
                    'RequestParameters': function['Api']['RequestParameters'] if 'RequestParameters' in function[
                        'Api'] else None,
                    'IntegrationRequestTemplates': function['Api'][
                        'IntegrationRequestTemplates'] if 'IntegrationRequestTemplates' in function[
                        'Api'] else None,
                }

                restApiId = regex.sub("", parameters['ApiName']) + 'api'
                restApi = RestApi(
                    restApiId,
                    Name=parameters["ApiName"],
                )
                restApiObj = AWSObject(restApiId, restApi)

                apiResourceObj = None
                apiResource = None
                for i, path in enumerate(str(parameters['Path']).split('/')):
                    apiResourceId = regex.sub("", path) + 'Path'
                    apiParameters = {
                        "RestApiId":Ref(restApi),
                        "ParentId": GetAtt(restApi, "RootResourceId") if i == 0 else Ref(apiResource),
                        "PathPart": path.replace("/", ""),
                    }
                    apiResource = Resource(
                        apiResourceId,
                        **dict((k, v) for k, v in apiParameters.iteritems() if v is not None)
                    )
                    apiResourceObj = AWSObject(apiResourceId, apiResource)
                    G.add_node(apiResourceObj)

                    if i == 0:
                        G.add_edge(apiResourceObj, restApiObj)
                    else:
                        prevPath = str(parameters['Path']).split('/')[i - 1]
                        G.add_edge(apiResourceObj, AWSObject(regex.sub("", prevPath) + 'Path'))

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
                            Uri=Join("", ["arn:aws:apigateway:us-east-1:lambda:action/", parameters['Uri']]),
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
                            Uri=Join("", ["arn:aws:apigateway:", Ref("AWS::Region"), ":lambda:path/2015-03-31/functions/", GetAtt(func, "Arn"), "/invocations"]),
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

                methodId =regex.sub("", parameters['HttpMethod']) + 'Method'
                method = Method(
                    methodId,
                    **dict((k, v) for k, v in methodParameters.iteritems() if v is not None)
                )
                methodObj = AWSObject(methodId, method)

                deploymentId = regex.sub("", parameters['ApiName']) + 'Deployment'
                deploymentParameters = {
                    "RestApiId":Ref(restApi),
                    "StageName":parameters['StageName'],
                    "Description":parameters['Description'] if 'Description' in parameters else None,
                    "DependsOn":regex.sub("", parameters['HttpMethod']) + 'Method',
                }
                deployment = Deployment(
                    deploymentId,
                    **dict((k, v) for k, v in deploymentParameters.iteritems() if v is not None)
                )
                deploymentObj = AWSObject(deploymentId, deployment)

                permissionId = regex.sub("", parameters['Path']) + 'Path' + 'Permission'
                permission = Permission(
                    permissionId,
                    Action="lambda:InvokeFunction",
                    Principal="apigateway.amazonaws.com",
                    SourceArn=Join("", ["arn:aws:execute-api:", Ref("AWS::Region"), ":", Ref("AWS::AccountId"), ":",
                                        Ref(restApi), "/*/", parameters['HttpMethod'], "/",
                                        str(parameters['Path'])]),
                    FunctionName=Ref(func),
                    DependsOn=regex.sub("", parameters['ApiName']) + 'Deployment'
                )
                permissionObj = AWSObject(permissionId, permission)

                G.add_node(methodObj)
                G.add_node(permissionObj)
                G.add_node(deploymentObj)

                G.add_edge(methodObj, apiResourceObj )
                G.add_edge(deploymentObj, methodObj)
                G.add_edge(permissionObj, restApiObj)
                G.add_edge(permissionObj,methodObj)
                G.add_edge(permissionObj, funcObj)
