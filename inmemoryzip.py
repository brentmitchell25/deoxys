from zipfile import ZipFile
from StringIO import StringIO

class InMemoryZipFile(object):
    def __init__(self):
        self.inMemoryOutputFile = StringIO()

    def write(self, inzipfilename, data):
        zip = ZipFile(self.inMemoryOutputFile, 'a')
        zip.writestr(inzipfilename, data)
        zip.close()

    def read(self):
        self.inMemoryOutputFile.seek(0)
        return self.inMemoryOutputFile.getvalue()

    def writetofile(self, filename):
        open('out.zip', 'wb').write(self.read())