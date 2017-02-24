from troposphere.apigateway import ApiKey, RestApi
import re

regex = re.compile('[^a-zA-Z]')


def apigateway(item, template, defaults):
    if 'Apis' in item:
        for api in item['Apis']:
            parameters = {
                "Body": api['Body'] if "Body" in api else None,
                "BodyS3Location": api['BodyS3Location'] if "BodyS3Location" in api else None,
                "CloneFrom": api['CloneFrom'] if "CloneFrom" in api else None,
                "Description": api['Description'] if "Description" in api else None,
                "FailOnWarnings": api['FailOnWarnings'] if "FailOnWarnings" in api else None,
                "Name": api['Name'],
                "Parameters": api['Parameters'] if "Parameters" in api else None,
            }

            template.add_resource(RestApi(
                regex.sub("", api['Name']) + 'api',
                **dict((k, v) for k, v in parameters.iteritems() if v is not None)
            ))
    return template
