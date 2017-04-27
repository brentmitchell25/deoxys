import unittest
from test_utilities import mapTestJsonFiles, mapJsonToYml, testYaml, getImmediateSubdirectories, unidiff_output

class TestAWSLambda(unittest.TestCase):
    def test_basic_function(self):
        testDirectories = getImmediateSubdirectories('test_input')
        for directory in testDirectories:
            json = mapTestJsonFiles(directory)
            ymlInput = mapJsonToYml(json)['services']
            ymlOutput = testYaml(ymlInput, inputDirectoryName=directory)
            self.assertEqual(ymlInput, ymlOutput, msg='{}\n{}'.format(directory,unidiff_output(ymlOutput, ymlInput)))


if __name__ == '__main__':
    unittest.main()
