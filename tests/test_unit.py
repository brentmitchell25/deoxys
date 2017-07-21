import unittest
from test_utilities import mapTestJsonFiles, mapJsonToYml, testYaml, getImmediateSubdirectories, unidiff_output

class TestUnit(unittest.TestCase):
    def test_input(self):
        testDirectories = getImmediateSubdirectories('test_input')
        for directory in testDirectories:
            json = mapTestJsonFiles(directory)
            ymlInput = mapJsonToYml(json)['services']
            ymlOutput = testYaml(ymlInput, inputDirectoryName=directory)
            try:
                self.assertEqual(ymlInput, ymlOutput, msg='{}\n{}'.format(directory,unidiff_output(ymlOutput, ymlInput)))
            except Exception, e:
                print(e)


if __name__ == '__main__':
    unittest.main()
