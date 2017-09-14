from troposphere.awslambda import Function, Code, Permission, VPCConfig, Environment
from troposphere.apigateway import RestApi, Resource, Method, Integration, Deployment, IntegrationResponse, \
    MethodResponse
from troposphere.events import Rule, Target
from troposphere.apigateway import RestApi, Resource, Method, Integration, Deployment, IntegrationResponse, \
    MethodResponse
from troposphere import FindInMap, GetAtt, Join, Output
from troposphere import Parameter, Ref, Template
from distutils.util import strtobool
import uuid
import re
import utilities
import os

lambdaImg = './AWS_Simple_Icons/Compute/Compute_AWSLambda.png'
apiGatewayImg = './AWS_Simple_Icons/Application Services/ApplicationServices_AmazonAPIGateway.png'
cloudwatchImg = './AWS_Simple_Icons/Management Tools/ManagementTools_AmazonCloudWatch_eventtimebased.png'
regex = re.compile('[^a-zA-Z0-9]')


def getRequestTemplate(params):
    if params is None:
        return None
    template = "{\n"
    for idx, val in enumerate(params):
        template += "\"" + val + "\": \"$input.params('" + val + "')\""
        if idx < len(params) - 1:
            template += ",\n"

    template += "\n}"
    retVal = {
        "application/json": template
    }
    return retVal


def getIntegrationResponse(params, isOptionsMethod=False):
    integrationResponseParameters = {
        'StatusCode': '200',
        'ResponseParameters': None
    }
    if str(params['Cors']).lower() == 'true':
        if isOptionsMethod:
            integrationResponseParameters['ResponseParameters'] = {
                "method.response.header.Access-Control-Allow-Headers": '\'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token\'',
                "method.response.header.Access-Control-Allow-Methods": '\'DELETE,GET,HEAD,OPTIONS,PATCH,POST,PUT\'',
                "method.response.header.Access-Control-Allow-Origin": '\'*\'',
            }
        else:
            integrationResponseParameters['ResponseParameters'] = {
                "method.response.header.Access-Control-Allow-Origin": '\'*\'',
            }
    return IntegrationResponse(**dict((k, v) for k, v in integrationResponseParameters.iteritems() if v is not None))


def getIntegration(params, isAsynchronous=False, func=None, isOptionsMethod=False):
    if str(params['Cors']).lower() and isOptionsMethod:
        integrationParameters = {
            'Type': "MOCK",
            'IntegrationResponses': [
                getIntegrationResponse(params=params, isOptionsMethod=isOptionsMethod)
            ],
            'RequestTemplates': {
                "application/json": '{\"statusCode\": 200}'
            },
        }
    elif str(params['Asynchronous']).lower() == 'true' and params['UrlQueryStringParameters'] is not None:
        integrationParameters = {
            'Type': "AWS",
            'Credentials': Join("", ["arn:aws:iam::", Ref("AWS::AccountId"), ":", "role/",
                                     params['Role']]),
            'IntegrationHttpMethod': "POST",
            'Uri': Join("", ["arn:aws:apigateway:us-east-1:lambda:path/",
                             params['Uri']]),
            'IntegrationResponses': [
                getIntegrationResponse(params=params)
            ],
            'RequestTemplates': getRequestTemplate(params['UrlQueryStringParameters']),
            'RequestParameters': {
                "integration.request.header.X-Amz-Invocation-Type": '\'Event\''
            }
        }
    elif isAsynchronous:
        integrationParameters = {
            'Type': "AWS",
            'Credentials': Join("", ["arn:aws:iam::", Ref("AWS::AccountId"), ":", "role/",
                                     params['Role']]),
            # IntegrationHttpMethod=str(parameters['HttpMethod']).upper(),
            'IntegrationHttpMethod': "POST",
            'Uri': Join("", ["arn:aws:apigateway:us-east-1:lambda:path/",
                             params['Uri']]),
            'IntegrationResponses': [
                getIntegrationResponse(params=params)
            ],
            'RequestParameters': {
                "integration.request.header.X-Amz-Invocation-Type": '\'Event\''
            }
        }
    elif params['UrlQueryStringParameters'] is not None:
        integrationParameters = {
            'Type': "AWS",
            'IntegrationHttpMethod': "POST",
            'Uri': Join("",
                        ["arn:aws:apigateway:", Ref("AWS::Region"),
                         ":lambda:path/2015-03-31/functions/",
                         GetAtt(func, "Arn"), "/invocations"]),
            'RequestTemplates': getRequestTemplate(params['UrlQueryStringParameters']),
            'IntegrationResponses': [
                getIntegrationResponse(params=params)
            ],
        }
    else:
        integrationParameters = {
            'Type': "AWS",
            # IntegrationHttpMethod=str(parameters['HttpMethod']).upper(),
            'IntegrationHttpMethod': "POST",
            'Uri': Join("",
                        ["arn:aws:apigateway:", Ref("AWS::Region"),
                         ":lambda:path/2015-03-31/functions/",
                         GetAtt(func, "Arn"), "/invocations"]),
            'IntegrationResponses': [
                getIntegrationResponse(params=params)
            ],
        }

    return Integration(
        **dict((k, v) for k, v in integrationParameters.iteritems() if v is not None)
    )


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
            SecurityGroupIds=(
                os.environ['LAMBDA_SECURITY_GROUPS'] if os.getenv('LAMBDA_SECURITY_GROUPS') else defaults.get('DEFAULT',
                                                                                                              'LambdaSecurityGroupIds')).split(
                ','),
            SubnetIds=(os.environ['LAMBDA_SUBNET_IDS'] if os.getenv('LAMBDA_SUBNET_IDS') else defaults.get('DEFAULT',
                                                                                                           'LambdaSubnetIds')).split(
                ',')
        )
    elif 'VpcConfig' in function and str(function['VpcConfig']).lower().strip() != "false":
        vpcConfig = VPCConfig(
            SecurityGroupIds=function['VpcConfig']['SecurityGroupIds'].split(','),
            SubnetIds=function['VpcConfig']['SubnetIds'].split(',')
        )
    return vpcConfig


def getTarget(poller, func, functionId):
    params = {
        "Arn": GetAtt(func, "Arn"),
        "Id": functionId,
        "Input": poller['Input'] if 'Input' in poller else None,
        "InputPath": poller['InputPath'] if 'InputPath' in poller else None
    }
    return Target(
        **dict((k, v) for k, v in params.iteritems() if v is not None)
    )


def getRule(pollerId, scheduleExpression, function, poller, func, functionId, index):
    return Rule(
        pollerId,
        Name=function['FunctionName'] + '-' + (poller['Name'] if 'Name' in poller else str(index)) + '-Poller',
        Description=function['FunctionName'] + " Poller",
        ScheduleExpression=scheduleExpression,
        State="DISABLED" if 'Enabled' in poller and str(
            poller['Enabled']).lower() == 'false' else 'ENABLED',
        Targets=[getTarget(poller, func=func, functionId=functionId)]
    )


def getMethodResponse(parameters, isOptionMethod=False):
    methodResponseParameters = {
        'StatusCode': '200',
        'ResponseParameters': None,
    }
    if str(parameters['Cors']).lower() == 'true':
        if isOptionMethod:
            methodResponseParameters['ResponseParameters'] = {
                'method.response.header.Access-Control-Allow-Headers': True,
                'method.response.header.Access-Control-Allow-Methods': True,
                'method.response.header.Access-Control-Allow-Origin': True,
            }
        else:
            methodResponseParameters['ResponseParameters'] = {
                'method.response.header.Access-Control-Allow-Origin': True,
            }
    return MethodResponse(
        **dict((k, v) for k, v in methodResponseParameters.iteritems() if v is not None)
    )


def awslambda(item, template, defaults, G, apiGatewayMap):
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
                    Variables={key: str(value) for key, value in
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

            graphFunctionId = functionId + item['Protocol']
            utilities.mergeNode(G, id=graphFunctionId, resource=func, image=lambdaImg, name=parameters['FunctionName'])

            if 'Poller' in function:
                if isinstance(function['Poller'], dict):
                    function['Poller'] = [function['Poller']]
                for idx, poller in enumerate(function['Poller']):
                    pollerId = regex.sub("", functionId + (poller['Name'] if 'Name' in poller else str(idx)) + 'Poller')
                    permissionId = regex.sub("", pollerId + 'Permission')
                    scheduleExpression = ""
                    if 'Rate' in poller:
                        scheduleExpression = "rate(" + str(poller['Rate']) + ")"
                    elif 'Cron' in poller:
                        scheduleExpression = "cron(" + str(poller['Cron']) + ")"
                    rule = getRule(pollerId, scheduleExpression=scheduleExpression, function=function, poller=poller,
                                   func=func, functionId=functionId, index=idx)
                    permission = Permission(
                        permissionId,
                        Action="lambda:InvokeFunction",
                        Principal="events.amazonaws.com",
                        SourceArn=GetAtt(rule, "Arn"),
                        FunctionName=Ref(func)
                    )
                    utilities.mergeNode(G, id=pollerId, resource=rule, image=cloudwatchImg,
                                        name=pollerId)
                    utilities.mergeNode(G, id=permissionId, resource=permission, image=cloudwatchImg,
                                        name=pollerId + ' InvokePermission')
                    G.add_edge(pollerId, graphFunctionId)
                    G.add_edge(permissionId, graphFunctionId)
                    G.add_edge(permissionId, pollerId)
            if 'Api' in function:
                if str(function['Api']['Path']).startswith('/'):
                    function['Api']['Path'] = str(function['Api']['Path'])[1:]
                if str(function['Api']['Path']).endswith('/'):
                    function['Api']['Path'] = str(function['Api']['Path'])[:-1]
                parameters = {
                    'RestApi': function['Api']['RestApi'],
                    'Path': function['Api']['Path'],
                    'HttpMethod': function['Api']['HttpMethod'],
                    'Asynchronous': function['Api']['Asynchronous'] if 'Asynchronous' in function['Api'] else 'false',
                    'Role': function['Api']['Role'] if 'Role' in function['Api'] else None,
                    'AuthorizationType': function['Api']['AuthorizationType'] if 'AuthorizationType' in function[
                        'Api'] else defaults.get('DEFAULT', 'AuthorizationType'),
                    'Uri': function['Api']['Uri'] if 'Uri' in function['Api'] else None,
                    'StageName': function['Api']['StageName'],
                    'UrlQueryStringParameters': function['Api'][
                        'UrlQueryStringParameters'] if 'UrlQueryStringParameters' in function[
                        'Api'] else None,
                    'RequestParameters': function['Api'][
                        'RequestParameters'] if 'RequestParameters' in function[
                        'Api'] else None,
                    'IntegrationRequestTemplates': function['Api'][
                        'IntegrationRequestTemplates'] if 'IntegrationRequestTemplates' in function[
                        'Api'] else None,
                    'Cors': function['Api']['Cors'] if 'Cors' in function['Api'] else None,
                }

                restApiId = None
                if 'Name' in parameters['RestApi']:
                    restApiId = regex.sub("", function['Api']['RestApi']["Name"]) + 'api'
                    restApi = RestApi(
                        restApiId,
                        Name=function['Api']['RestApi']["Name"],
                    )
                    utilities.mergeNode(G, id=restApiId, resource=restApi, image=apiGatewayImg,
                                        name=function['Api']['RestApi']["Name"])

                    apiId = Ref(restApi)
                    resourceId = GetAtt(restApi, "RootResourceId")
                    deploymentType = 'Name'
                else:
                    apiId = str(function['Api']['RestApi']['Id'])
                    resourceId = str(function['Api']['RestApi']["ResourceId"])
                    deploymentType = 'RestApiId'

                apiResource = None
                pathToMethod = ""
                if 'Path' in parameters:
                    for i, path in enumerate(str(parameters['Path']).split('/')):
                        pathToMethod = "/" + path
                        apiResourceId = regex.sub("", path) + 'Path'
                        apiParameters = {
                            "RestApiId": apiId,
                            "ParentId": resourceId if i == 0 else Ref(apiResource),
                            "PathPart": path.replace("/", ""),
                        }
                        apiResource = Resource(
                            apiResourceId,
                            **dict((k, v) for k, v in apiParameters.iteritems() if v is not None)
                        )
                        utilities.mergeNode(G, id=apiResourceId, resource=apiResource, image=apiGatewayImg,
                                            name=regex.sub("", path))
                        if i == 0:
                            if 'Name' in parameters['RestApi']:
                                G.add_edge(apiResourceId, restApiId)
                        else:
                            prevPath = str(parameters['Path']).split('/')[i - 1]
                            G.add_edge(apiResourceId, regex.sub("", prevPath) + 'Path')

                corsMethodId = None
                if str(parameters['Cors']).lower() == 'true':
                    corsMethodParameters = {
                        "RestApiId": apiId,
                        "ResourceId": resourceId if apiResource is None else Ref(apiResource),
                        "HttpMethod": 'OPTIONS',
                        "AuthorizationType": 'NONE',
                        "Integration": getIntegration(parameters, isOptionsMethod=True),
                        "MethodResponses": [
                            getMethodResponse(parameters=parameters, isOptionMethod=True)
                        ],
                    }
                    corsMethodId = regex.sub("", pathToMethod) + 'Cors'
                    corsMethod = Method(
                        corsMethodId,
                        **dict((k, v) for k, v in corsMethodParameters.iteritems() if v is not None)
                    )

                    utilities.mergeNode(G, id=corsMethodId, resource=corsMethod, image=apiGatewayImg,
                                        name=pathToMethod + 'CorsMethod')

                if str(parameters['Asynchronous']).lower() == 'true':
                    methodParameters = {
                        "RestApiId": apiId,
                        "ResourceId": resourceId if apiResource is None else Ref(apiResource),
                        "HttpMethod": str(parameters['HttpMethod']).upper(),
                        "AuthorizationType": parameters['AuthorizationType'],
                        "Integration": getIntegration(parameters, isAsynchronous=True, func=func),
                        "MethodResponses": [
                            getMethodResponse(parameters=parameters)
                        ],
                    }
                else:
                    methodParameters = {
                        "RestApiId": apiId,
                        "ResourceId": resourceId if apiResource is None else Ref(apiResource),
                        "HttpMethod": str(parameters['HttpMethod']).upper(),
                        "AuthorizationType": parameters['AuthorizationType'],
                        "Integration": getIntegration(parameters, isAsynchronous=False, func=func),
                        "RequestParameters": dict(
                            ("method.request.querystring." + (v if 'Name' not in v else v),
                             bool(strtobool(defaults.get('DEFAULT', 'QueryStringRequired')))
                             if 'Required' not in v else bool(strtobool(str(v))))
                            for v in parameters['UrlQueryStringParameters'])
                        if parameters['UrlQueryStringParameters'] is not None else None,
                        "RequestTemplates": parameters['RequestParameters'],
                        "MethodResponses": [
                            getMethodResponse(parameters=parameters)
                        ],
                    }
                methodId = regex.sub("", pathToMethod + parameters['HttpMethod']) + 'Method'
                method = Method(
                    methodId,
                    **dict((k, v) for k, v in methodParameters.iteritems() if v is not None)
                )
                utilities.mergeNode(G, id=methodId, resource=method, image=apiGatewayImg,
                                    name='Te' + '-' + str(parameters['HttpMethod']).upper())

                # Find any other associated lambdas with the same API to prevent multiple deployment objects
                mapId = '{0}{1}'.format(restApiId if restApiId is not None else apiId, parameters['StageName'])
                if mapId in apiGatewayMap[deploymentType]:
                    deploymentId = apiGatewayMap[deploymentType][mapId]
                else:
                    # Requires uuid to signal a change for CloudFormation to update the stack
                    deploymentId = regex.sub("", str(apiId) + str(uuid.uuid4())) + 'Deployment'
                    deploymentParameters = {
                        "RestApiId": apiId,
                        "StageName": parameters['StageName'],
                        "Description": parameters['Description'] if 'Description' in parameters else None,
                    }
                    deployment = Deployment(
                        deploymentId,
                        **dict((k, v) for k, v in deploymentParameters.iteritems() if v is not None)
                    )
                    utilities.mergeNode(G, id=deploymentId, resource=deployment, image=apiGatewayImg,
                                        name=parameters['StageName'] + "-Deployment")
                    apiGatewayMap[deploymentType][mapId] = deploymentId

                permissionId = regex.sub("", parameters['Path']) + parameters['HttpMethod'] + 'Path' + 'Permission'
                permission = Permission(
                    permissionId,
                    Action="lambda:InvokeFunction",
                    Principal="apigateway.amazonaws.com",
                    SourceArn=Join("", ["arn:aws:execute-api:", Ref("AWS::Region"), ":", Ref("AWS::AccountId"), ":",
                                        apiId, "/*/", parameters['HttpMethod'], "/",
                                        str(parameters['Path'])]),
                    FunctionName=Ref(func),
                )
                utilities.mergeNode(G, id=permissionId, resource=permission, image=lambdaImg,
                                    name="InvokeFunctionPermission")

                G.add_edge(methodId, apiResourceId)
                G.add_edge(deploymentId, methodId)
                G.add_edge(permissionId, methodId)
                G.add_edge(permissionId, graphFunctionId)

                if corsMethodId is not None:
                    G.add_edge(corsMethodId, apiResourceId)
                    G.add_edge(deploymentId, corsMethodId)
                if restApiId is not None:
                    G.add_edge(permissionId, restApiId)
