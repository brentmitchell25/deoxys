class AWSObject(object):
    def __init__(self, id, troposphereResource=None):
        self.id = id
        self.troposphereResource = troposphereResource

    def __key(self):
        return (self.id)

    def __hash__(self):
        return(hash(self.__key()))

    def __eq__(self, other):
        return(self.__key() == other.__key())

    def __str__(self):
        return(self.id)