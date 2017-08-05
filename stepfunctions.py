from troposphere.stepfunctions import StateMachine, Activity
from troposphere import Join
from troposphere import Ref
import utilities
import re

regex = re.compile('[^a-zA-Z0-9]')

stepFunctionsImg = './AWS_Simple_Icons/Application Services/ApplicationServices_AWSStepFunctions.png'


def getStateMachine(stepFunction):
    if 'StateMachine' not in stepFunction:
        return None
    return {
        'DefinitionString': stepFunction['StateMachine']['DefinitionString'],
        'RoleArn': Join("",
                        ["arn:aws:iam::",
                         Ref(
                             "AWS::AccountId"),
                         ":role/",
                         stepFunction['StateMachine']['Role']]),
    }


def getActivity(stepFunction):
    if 'Activity' not in stepFunction:
        return None
    return {
        'Name': stepFunction['Activity']['Name']
    }


def stepfunctions(item, G, defaults):
    if 'StepFunctions' in item:
        for stepFunction in item['StepFunctions']:
            parameters = {
                "Activity": getActivity(stepFunction),
                "StateMachine": getStateMachine(stepFunction)
            }

            if parameters['Activity'] is not None:
                activityId = regex.sub("", parameters['Activity']['Name']) + 'Activity'
                activity = Activity(
                    activityId,
                    **dict((k, v) for k, v in parameters['Activity'].iteritems() if v is not None)
                )
                utilities.mergeNode(G, id=activityId, resource=activity, image=stepFunctionsImg,
                                    name=parameters['Activity']['Name'])

            if parameters['StateMachine'] is not None:
                stateMachineId = utilities.capString(regex.sub("", parameters['StateMachine']['DefinitionString']) + 'StateMachine', 80)
                print stateMachineId
                stateMachine = StateMachine(
                    stateMachineId,
                    **dict((k, v) for k, v in parameters['StateMachine'].iteritems() if v is not None)
                )
                utilities.mergeNode(G, id=stateMachineId, resource=stateMachine, image=stepFunctionsImg,
                                    name='StateMachine')
