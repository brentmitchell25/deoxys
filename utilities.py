import matplotlib.image as mpimg

def mergeNode(G, id, resource, image, name):
    # canInsert = True
    # for n in G:
    #     if str(n) == id:
    #         # print(n)
    #         G[id]['resource'] = resource
    #         G[id]['image'] = image
    #         # G[id]['name'] = name
    #         canInsert = False
    #         break
    #
    # if canInsert:
    img = mpimg.imread(image)
    G.add_node(id, resource=resource, image=image, label=name)


    # if G.has_node(str(id).strip()):
    #     print(G.node[id])
    #     G[id]['resource'] = resource
    #     G[id]['image'] = image
    #     G[id]['name'] = name
    # else:
    #     G.add_node(id, resource=resource, image=image, name=name)
