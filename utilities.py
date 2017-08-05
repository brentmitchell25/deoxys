def mergeNode(G, id, resource, image, name):
    G.add_node(id, resource=resource, image=image, label=name)

def capString(s, l):
    return s if len(s) <= l else s[0:l]