from AWSObject import AWSObject


def insertIntoGraph(G, uId, vId, resource):
    if G.has_node(AWSObject(id)):
        G.add_edge(AWSObject(id=uId), AWSObject(id=vId))
    else:
        G.add_edge(AWSObject(id=uId), AWSObject(troposphereResource=resource, id=vId))
