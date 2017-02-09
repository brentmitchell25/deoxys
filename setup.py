import os.path
import configparser

if not os.path.exists("defaults.ini"):
    replaceFile = raw_input("Defaults file already detected, would you like to replace the current one?")
    if replaceFile.strip().lower() == "y" or replaceFile.strip().lower() == "yes":
        print("Did not replace the defaults file. Exiting.")

config = configparser.ConfigParser()

config['DEFAULT'] = {
    'CloudformationBucket' = 'TODO',

}