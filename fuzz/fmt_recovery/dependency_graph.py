#!/usr/bin/env python3

import sys
import glob
import os
import re
import pickle
import networkx as nx
import matplotlib.pyplot as plt

def createGraph():
    dg = nx.MultiDiGraph()

    dg.add_node("generate_key", entry=True)
    dg.add_node("import_key", entry=True)

    dg.add_node("export_key", entry=False)
    dg.add_node("get_key_characteristics", entry=False)
    dg.add_node("delete_key", entry=False)
    dg.add_node("begin", entry=False)
    dg.add_node("update", entry=False)
    dg.add_node("finish", entry=False)
    dg.add_node("abort", entry=False)

    # data dependencies
    dg.add_edge("generate_key", "get_key_characteristics", eType="dataDep", key=0)
    dg.add_edge("generate_key", "export_key", eType="dataDep", key=0)
    dg.add_edge("generate_key", "begin", eType="dataDep", key=0)
    dg.add_edge("generate_key", "delete_key", eType="dataDep", key=0)

    dg.add_edge("import_key", "get_key_characteristics", eType="dataDep", key=0)
    dg.add_edge("import_key", "export_key", eType="dataDep", key=0)
    dg.add_edge("import_key", "begin", eType="dataDep", key=0)
    dg.add_edge("import_key", "delete_key", eType="dataDep", key=0)

    dg.add_edge("begin", "update", eType="dataDep", key=0)
    dg.add_edge("begin", "finish", eType="dataDep", key=0)
    dg.add_edge("begin", "abort", eType="dataDep", key=0)

    # transition dependencies
    dg.add_edge("generate_key", "get_key_characteristics", eType="trans", key=1)
    dg.add_edge("generate_key", "export_key", eType="trans", key=1)
    dg.add_edge("generate_key", "begin", eType="trans", key=1)
    dg.add_edge("generate_key", "delete_key", eType="trans", key=1)

    dg.add_edge("import_key", "export_key", eType="trans", key=1)
    dg.add_edge("import_key", "get_key_characteristics", eType="trans", key=1)
    dg.add_edge("import_key", "begin", eType="trans", key=1)
    dg.add_edge("import_key", "delete_key", eType="trans", key=1)

    dg.add_edge("export_key", "export_key", eType="trans", key=1)
    dg.add_edge("export_key", "get_key_characteristics", eType="trans", key=1)
    dg.add_edge("export_key", "begin", eType="trans", key=1)
    dg.add_edge("export_key", "delete_key", eType="trans", key=1)

    dg.add_edge("get_key_characteristics", "get_key_characteristics", eType="trans", key=1)
    dg.add_edge("get_key_characteristics", "export_key", eType="trans", key=1)
    dg.add_edge("get_key_characteristics", "begin", eType="trans", key=1)
    dg.add_edge("get_key_characteristics", "delete_key", eType="trans", key=1)

    dg.add_edge("begin", "update", eType="trans", key=1)
    dg.add_edge("begin", "finish", eType="trans", key=1)
    dg.add_edge("begin", "abort", eType="trans", key=1)

    dg.add_edge("update", "update", eType="trans", key=1)
    dg.add_edge("update", "finish", eType="trans", key=1)
    dg.add_edge("update", "abort", eType="trans", key=1)

    dg.add_edge("abort", "export_key", eType="trans", key=1)
    dg.add_edge("abort", "get_key_characteristics", eType="trans", key=1)
    dg.add_edge("abort", "delete_key", eType="trans", key=1)

    dg.add_edge("finish", "export_key", eType="trans", key=1)
    dg.add_edge("finish", "get_key_characteristics", eType="trans", key=1)
    dg.add_edge("finish", "delete_key", eType="trans", key=1)
    return dg

def drawGraph(dg):
    nx.draw(dg, pos=nx.circular_layout(dg), nodecolor='r', edge_color='b')
    labels=nx.draw_networkx_labels(dg,pos=nx.circular_layout(dg))
    plt.show()

def fillGraph(dg, path):
    depNodes = set()

    for edge in dg.edges():
        depNodes.add(edge[1])

    for node in dg.nodes():
        if (node not in depNodes):
            continue
        for filename in glob.glob(os.path.join(path, '*', "onleave", node + "_*")):
            predNodes = dg.predecessors(node)

            # check if node has a data dependency on a predecessor node
            dataDep = []
            for pred in predNodes:
                curPred = pred
                #if(dg.node[pred]['entry']):

                for index in dg.get_edge_data(pred, node):
                    if(dg.get_edge_data(pred, node)[index]['eType'] == 'dataDep'):
                        dataDep.append(pred)
                if (len(dataDep) == 0):
                    continue

            # get number of function call and search in all predecessor dirs for pred call
            callNr = int(os.path.basename(os.path.dirname(os.path.dirname(filename))))

            for fromFile in os.listdir(path):
                if(callNr <= int(fromFile)):
                    continue

                # check for data dependency between function calls
                match = False
                fromFunc = ""
                for fname in os.listdir(os.path.join(path, fromFile, 'onenter')):
                    if (re.match(r".*\_[0-9]+$", fname)):
                        func = re.sub('\_[0-9]+$', '', fname)
                        if (func in dataDep):
                            fromFunc = func
                            match = True

                if (not match):
                    continue

                fromDir = os.path.join(path, fromFile, "onleave")
                toDir = os.path.join(path, str(callNr), "onenter")

                if(os.path.isfile(os.path.join(fromDir, "resp.types")) and os.path.isfile(os.path.join(toDir, "req.types"))):
                    fromTypes = pickle.load(open(os.path.join(fromDir, "resp.types"), "rb"), encoding="latin1")
                    toTypes = pickle.load(open(os.path.join(toDir, "req.types"), "rb"), encoding="latin1")
                else:
                    print("No '*.types' file available for dependency: " + fromFunc + " (" + str(fromFile) + ") -> " + node + " (" + str(callNr) + ")")
                    # TODO: Fallback if one File does not exist
                    continue

                fromData = open(os.path.join(fromDir, "resp"), "rb")
                toData = open(os.path.join(toDir, "req"), "rb")

                curSize = 0
                curToOff = 0
                curFromOff = 0
                sizeDict = None

                for (offsetFrom, sizeFrom), fromType in fromTypes:
                    if(curSize == -1):
                        break
                    for (offsetTo, sizeTo), toType in toTypes:
                        # TODO type must be equal?
                        if (sizeFrom == sizeTo):
                            fromData.seek(offsetFrom)
                            fromBytes = fromData.read(sizeFrom)
                            toData.seek(offsetTo)
                            toBytes = toData.read(sizeTo)
                            # Assumptions: Matching Data not only Null bytes, the biggest match is used, match must be bigger than 4 Bytes
                            # TODO: Distance between calls important?
                            if(fromBytes == toBytes and int.from_bytes(fromBytes, byteorder='big', signed=False) != 0 and sizeFrom > curSize and sizeFrom > 4):
                                foundDep = True
                                curFromOff = offsetFrom
                                curToOff = offsetTo

                                # if size divers in multiple calls -> size is variable
                                if ('attr_dict' in dg[fromFunc][node][0]):
                                    if(dg[fromFunc][node][0]['attr_dict']['fromOff'] == offsetFrom
                                        and dg[fromFunc][node][0]['attr_dict']['toOff'] == offsetTo
                                        and dg[fromFunc][node][0]['attr_dict']['size'] != sizeFrom):

                                        curSize = -1

                                        if(dg[fromFunc][node][0]['attr_dict']['size'] == -1):
                                            break

                                        # get size offset from buffer -> assuming size is 4 Byte
                                        # TODO: maybe 8 Byte?
                                        fromData.seek(0)
                                        sizeBytes = fromData.read(4)
                                        count = 0

                                        while (sizeBytes):
                                            if(int.from_bytes(sizeBytes, byteorder='little', signed=False) == sizeFrom):
                                                print("     -> Variable size info found at offset " + str(4*count))
                                                sizeDict = {'offset':count*4, 'size':4}
                                                break
                                            count += 1
                                            sizeBytes = fromData.read(4)
                                            if(count > 10):
                                                break
                                        break

                                if (curSize <= sizeFrom):
                                    print("Data dep from " + fromFunc + " (" + str(fromFile) + ") to " + node + " (" + str(callNr) + ") with " + str(sizeFrom) + " Bytes found!")
                                    curSize = sizeFrom

                # if size info was found -> set in graph
                if(curSize != 0):
                    infoDict = {'fromOff':curFromOff, 'toOff':curToOff, 'size':curSize}
                    dg.add_edge(fromFunc, node, key=0, attr_dict=infoDict)
                    if('size_dict' not in dg[fromFunc][node][0]):
                        if(curSize == -1 and sizeDict != None):
                            dg.add_edge(fromFunc, node, key=0, size_dict=sizeDict)
                        elif(curSize == -1 and sizeDict == None):
                            sizeDict = {'offset':-1, 'size':-1}
                            dg.add_edge(fromFunc, node, key=0, size_dict=sizeDict)
                            print(" Error: No size information for dependency found!")

def get_dependencies(dg, node):
    predNodes = dg.predecessors(node)

    # check if node has a data dependency on a predecessor node
    dataDeps = []
    ret = []

    for pred in predNodes:
        curPred = pred

        for index in dg.get_edge_data(pred, node):
            if(dg.get_edge_data(pred, node)[index]['eType'] == 'dataDep'):
                dataDeps.append(pred)

    for dataDep in dataDeps:
        if ('attr_dict' in dg[dataDep][node][0]):
            if ('size_dict' in dg[dataDep][node][0]):
                ret.append((dataDep, dg[dataDep][node][0]['attr_dict']['fromOff'], dg[dataDep][node][0]['attr_dict']['toOff'], dg[dataDep][node][0]['attr_dict']['size'],
                dg[dataDep][node][0]['size_dict']['offset'], dg[dataDep][node][0]['size_dict']['size']))
            elif (dg[dataDep][node][0]['attr_dict']['size'] == -1):
                ret.append((dataDep, dg[dataDep][node][0]['attr_dict']['fromOff'], dg[dataDep][node][0]['attr_dict']['toOff'], dg[dataDep][node][0]['attr_dict']['size'], 0, 0))
            else:
                ret.append((dataDep, dg[dataDep][node][0]['attr_dict']['fromOff'], dg[dataDep][node][0]['attr_dict']['toOff'], dg[dataDep][node][0]['attr_dict']['size']))
        else:
            ret.append((dataDep, 0, 0, 0))

    return ret

if __name__ == "__main__":
    if(len(sys.argv) != 2):
        print("Call with path!!!")
        sys.exit(0)

    dg = createGraph()
    #drawGraph(dg)
    fillGraph(dg, sys.argv[1])
    print('')
    for node in dg.nodes():
        data = get_dependencies(dg, node)
        for cur in data:
            print(str(cur) + " -> " + node)
