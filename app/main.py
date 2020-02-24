import json
import os
import random
import bottle
import math
import copy

from api import ping_response, start_response, move_response, end_response

"""
0 = empty space
1 = food
2 = enemy head
3 = my head
4 = my snaky body
5 = other snake bodies
"""
SPACE = 0
FOOD = 1
HEAD = 2
MYHEAD = 3
SELF = 4
BODY = 5

@bottle.route('/')
def index():
    return '''
    Battlesnake documentation can be found at
       <a href="https://docs.battlesnake.io">https://docs.battlesnake.io</a>.
    '''

@bottle.route('/static/<path:path>')
def static(path):
    """
    Given a path, return the static file located relative
    to the static folder.

    This can be used to return the snake head URL in an API response.
    """
    return bottle.static_file(path, root='static/')

@bottle.post('/ping')
def ping():
    """
    A keep-alive endpoint used to prevent cloud application platforms,
    such as Heroku, from sleeping the application instance.
    """
    return ping_response()

@bottle.post('/start')
def start():
    data = bottle.request.json
    print(json.dumps(data))

    color = "#00FFFF"

    return start_response(color)

def initBoard(height, width, char=0):
    """creates an empty board(filled with 0's)
    
    Arguments:\n
        height {int} -- the height of the board
        width {int} -- the width of the board
    
    Returns:
        list of lists -- the empty board
    """
    arr = []
    for _ in range(height):
        arr.append([])
        for _ in range(width):
            arr[-1].append(char)
    return arr

def makeBoard(data):
    """creates a board to model what is going on in the game
    
    Arguments:\n
        data {dict} -- the game information
    
    Returns:
        list of list of ints -- the model of what is going on,
            for details of values see top of file
    """
    board = data["board"]
    arr = initBoard(board["height"], board["width"])
    
    #food
    for meal in board["food"]:
        arr[meal["y"]][meal["x"]] = FOOD

    #snakes

    for snake in board["snakes"]:
        isSelf = False
        if snake["id"] == data["you"]["id"]:
            isSelf = True
        x,y = snake["body"][0]["x"], snake["body"][0]["y"]
        if isSelf:
            arr[y][x] = MYHEAD
        else:
            arr[y][x] = HEAD

        if data["turn"] == 0: #there will be no other bodies
            return arr

        for part in snake["body"][1:-1]:#-1 so doesnt count tail
            if isSelf:
                arr[part["y"]][part["x"]] = SELF
            else:
                arr[part["y"]][part["x"]] = BODY
    
    #showArr(arr)
    return arr

def showArr(arr):
    """shows an array, for debugging ONLY
    
    Arguments:\n
        arr {list of lists} -- the array to be shown
    """
    for line in arr:
        for char in line:
            if char == 0:
                print("0 ", end="")

            else:
                print(char,"", end="")
        print()
def headPos(data):
    """gets the position of our snakes head
    
    Arguments:\n
        data {dict} -- the game data
    
    Returns:
        tuple -- x,y coordinates of the head
    """
    headTemp = data["you"]["body"][0]
    return (headTemp["x"],headTemp["y"])

def noEnemies(data):
    """checks if there are any enemies on the board
    
    Arguments:\n
        data {dict} -- the game data
    
    Returns:
        boolean -- true if no other snakes around, else false
    """
    return len(data["board"]["snakes"])-1 == 0


def retracePath(parents, finalNode, start):
    """retraces path from destination to start
    
    Arguments:\n
        parents {dict} -- has [parent]:children relationships
        finalNode {tuple} -- x,y coordinates of final element in path
        start {tuple} -- x,y coordinates of first element in path
    
    Returns:
        list of tuples -- path from start to finalNode
    """
    path=[finalNode]
    v = finalNode
    while v != start:
        v = parents[v]
        path.insert(0, v)
    return path

def funkyNewBoard(board, body, pathLen):
    #board but without tail, length of pathLength
    nuBoard = copy.deepcopy(board)
    pathLen -= 1
    removedSegments = body[-pathLen:]
    leftovers = body[:-pathLen]
    for x, y in removedSegments:
        nuBoard[y][x] = 0
    for x,y in leftovers:
        nuBoard[y][x] = 4
    
    newHead = leftovers[0]
    nuBoard[newHead[1]][newHead[0]]=3
    
    return nuBoard

def listifyMyBody(data):
    li=[]
    for segment in data["you"]["body"][:-1]:
        li.append((segment["x"], segment["y"]))
    return li

#TODO change where enemies are, remove tails and maybe project heads
def fixTail(futureAdj, board, path, data):
    pathLen = len(path)
    body = listifyMyBody(data)
    body = path[::-1] + body[1:]#[1:] so doesnt duplicate head
    newBoard = funkyNewBoard(board, body, pathLen)
    for segment in body[-(pathLen-1):]:
        adjNodes = getAdjNodes(newBoard, segment[0], segment[1], True)
        for node in adjNodes:#adding connections back in
            if node in futureAdj and not segment in futureAdj[node][0]:
                futureAdj[node][0].append(segment)
        futureAdj[segment] = [adjNodes, 0, 1]

def possibleAdj(adjLi, board, path, data):
    """makes the adjacency list that would result from taken a given path
    note that doesnt remove parts of snake that are no longer there
    
    Arguments:\n
        adjLi {dict} -- the original ajacency list
        path {list of tuples} -- the list of x,y coordinates of nodes to be travelled
    
    Returns:
        dictionary -- the adjacency list if the path is taken
    """
    #newLi = adjLi.copy()#DOES NOT WORK
    newLi = copy.deepcopy(adjLi)
    for nodeKey in path[:-1]:
        delAdjNode(newLi, nodeKey)
    newLi[path[-1]][1]=3
    fixTail(newLi, board, path, data)
    return newLi

#jan 19 csc labs start

def isSuicide(adjLi, path, board, data):
    """checks if a given path would likely lead to premature snake death
    
    Arguments:\n
        adjLi {dict} -- the adjacency list
        path {list of tuples} -- nodes the snake would take
    
    Returns:
        boolean -- true if is probably suicide, else false
    """
    head = path[-1]
    futureAdj = possibleAdj(adjLi, board, path, data)
    adjLi[head][1] = MYHEAD#so doesnt find itself
    minDist = pathToThing(futureAdj, head, FOOD)
    if type(minDist) != int:
        minDist = len(minDist)
    
    adjLi[head][1] = FOOD#so doesnt find itself
    return minDist == -1#no path to food from destination

def viewAdjLi(adjLi, data):
    emptyBoard = initBoard(data["board"]["height"], data["board"]["width"], "D")
    for key in adjLi:
        emptyBoard[key[1]][key[0]] = adjLi[key][1]
    showArr(emptyBoard)

def dirToAdj(head, adj):
    """finds the direction from one node to an adjacent one.
    
    Arguments:\n
        head {tuple} -- the x,y coordinates of the node being looked from.
        adj {tuple} -- the x,y coordinates of the node being looked towards.
    
    Returns:
        string -- move_response that would get from head to adj.
    """
    theDir="up"
    if adj[1] == head[1]-1:
        theDir = "up"
    elif adj[1] == head[1]+1:
        theDir = "down"
    elif adj[0] == head[0]+1:
        theDir = "right"
    elif adj[0] == head[0]-1:
        theDir = "left"
    return move_response(theDir)

def getAdjNodes(board, x, y, all=False):
    """finds the adjacent nodes of a node.
    
    Arguments:\n
        board {list of lists} -- the board on which the snakes slither.
        x {int} -- the x position of the square being checked.
        y {int} -- the y position of the square being checked.
    
    Returns:
        list of tuples -- the keys of adjacent nodes
    """
    adj = []
    if x > 0 and board[y][x-1] < SELF:
        adj.append((x-1, y))
    if y > 0 and board[y-1][x] < SELF:
        adj.append((x, y-1))
    if all:
        if x < len(board)-1 and board[y][x+1] < SELF:
            adj.append((x+1, y))
        if y < len(board[0])-1 and board[y+1][x] < SELF:
            adj.append((x, y+1))
    return adj

def makeWeightBFS(adjLi, startPoint, starting_value):
    visitQueue = [startPoint]
    parents={}
    while visitQueue: #is false only if empty
        baseKey = visitQueue.pop()
        currLvl = adjLi[baseKey][2]//1.5
        if currLvl <= 0:#wont have any more impact
            break

        for adjNode in adjLi[baseKey][0]:
            if adjNode not in parents.keys(): #if undiscovered
                parents[adjNode] = baseKey #mark parent relationship
                adjWeight = adjLi[adjNode][2]
                if adjWeight < currLvl:
                    adjLi[adjNode][2] = currLvl
                elif adjWeight == currLvl:
                    adjLi[adjNode][2] = currLvl+1

                visitQueue.insert(0, adjNode)


def initDijkUndiscovered(adjLi, currPos):
    table = {}
    for key in adjLi.keys():
        table[key] = math.inf
    table[currPos] = 0
    return table

def minUndiscovered(undiscovered):
    minKey = None
    minPathLen = math.inf
    for key, nodePath in undiscovered.items():
        if nodePath < minPathLen or minKey is None:
            minPathLen = nodePath
            minKey = key
    if minPathLen == math.inf:#not reachable by head
        return None
    return minKey

def makeDijk(adjLi, currPos):
    dijkTable = {}#form is (x, y):[minDist, lastVertex] #start as (x,y):[None,None]
    undiscovered = initDijkUndiscovered(adjLi, currPos)
    while len(undiscovered) > 0:
        nextNode = minUndiscovered(undiscovered)
        if nextNode is None:#isnt reachable by head
            break
        currPathLen = dijkTable[nextNode][0] if nextNode in dijkTable else 0
        for adjNode in adjLi[nextNode][0]:
            lenToNode = currPathLen + adjLi[adjNode][2]

            if adjNode in undiscovered and lenToNode < undiscovered[adjNode]:
                undiscovered[adjNode] = lenToNode
                dijkTable[adjNode] = [lenToNode, nextNode]
            elif adjNode in dijkTable and lenToNode < dijkTable[adjNode][0]:
                dijkTable[adjNode] = [lenToNode, nextNode]
        del undiscovered[nextNode]#has now been discovered
    #print("AYAYA", "head at", currPos, adjLi, "dijk", dijkTable)
    return dijkTable

def makeWeightedAdj(adjLi, data):
    WEIGHT_START = 50
    for snake in data["board"]["snakes"]:
        if snake["id"] == data["you"]["id"]:
            continue
        snakeHead = snake["body"][0]
        snakeHead = (snakeHead["x"], snakeHead["y"])
        adjLi[snakeHead][2] = WEIGHT_START
        makeWeightBFS(adjLi, snakeHead, WEIGHT_START)



def makeAdjList(board):
    """makes the adjacency list for possible squares the snake can traverse
    
    Arguments:\n
        board {list of lists} -- the board with ints defining what is there
            see CONSTANTS at top of file for more info.
    
    Returns:
        dictionary -- the adjacency list, with keys being x,y tuple coordinate
            of the square and value being a list.
                [0] is list of adjacent nodes.
                [1] is int identity of node, see top of file again.
                [2] is weight of the node
    """
    #showArr(board)
    adjLi = {}
    for y, line in enumerate(board):
        for x, el in enumerate(line):
            key = (x,y)
            if el < SELF:#if can be traversed through
                adjNodes = getAdjNodes(board, x, y)
                for node in adjNodes:
                    adjLi[node][0].append(key)
                adjLi[key] = [adjNodes, el, 1]
    return adjLi

def delAdjNode(adjLi, delNode):
    """deletes a node and anything referenceing it from the adjacency list
    
    Arguments:\n
        adjLi {dict} -- the adjacency list.
        delNode {tuple} -- the node to be deleted.
    """
    #if delNode not in adjLi:
     #   return
    for connected in adjLi[delNode][0]:
        adjLi[connected][0].remove(delNode)
    del adjLi[delNode]

def selfLength(data):
    """finds how long the snake is
    
    Arguments:\n
        data {dict} -- the game data
    
    Returns:
        int -- the snakes length
    """
    return len(data["you"]["body"])

#TODO redo the docs on this one
def snakeIsHungry(foodPath, currHp, bodyLen):
    """determines if the snake has enough time to make it to
    the nearest food
    
    Arguments:\n
        currPos {tuple} -- the x,y coordinate of the snakes head
        currHp {int} -- how much health the snake has remaining
        bodyLength {int} -- how long the snake is
    
    Returns:
        boolean -- True if is in danger of starvation, else False
    """
    if foodPath is None:
        return False

    return len(foodPath) > currHp-bodyLen

def tailPos(data):
    """gets the position of the tail of the snake
    
    Arguments:\n
        data {dict} -- the game data
    
    Returns:
        tuple -- x,y coordinate of the tail
    """
    tailSegment = data["you"]["body"][-1]
    return (tailSegment["x"], tailSegment["y"])

#can pass either int or tuple as target
def pathToThing(adjLi, headPos, target):
    """finds the shortest path to a target from the head position
    
    Arguments:\n
        adjLi {dict} -- the adjacency list
        headPos {tuple} -- the starting position position
        target {tuple or int} -- if is an int will find corresponding 
            square with that type, if is tuple will find that specific coordinate
    
    Returns:
        list of tuples or int -- if list of tuples the path to get to target,
            if there is no path it returns -1
    """
    visitQueue = [headPos]
    parents = {}
    while visitQueue: #is false only if empty
        baseKey = visitQueue.pop()
        for adjNode in adjLi[baseKey][0]:
            if adjNode not in parents.keys(): #if undiscovered
                parents[adjNode] = baseKey #mark parent relationship
                #if adjNode not in adjLi:
                #    print("generalAYAYA", "head at",headPos, "going to", target, adjNode, adjLi)
                if adjNode == target or adjLi[adjNode][1] == target:
                    path = retracePath(parents, adjNode, headPos)
                    return path

                visitQueue.insert(0, adjNode)
    return -1

def regularDFS(adjLi, currPos, visited):
    visited.append(currPos)
    for adj in adjLi[currPos][0]:
        if adj in visited:
            continue
        regularDFS(adjLi, adj, visited)

    return visited

dirAdds = ((-1,0),(1,0),(0,-1), (0,1))
def areAdjacent(a, b):
    xa, ya = a[0], a[1]
    xb, yb = b[0], b[1]
    for xAdd, yAdd in dirAdds:
        if xa + xAdd == xb and ya + yAdd == yb:
            return True
    return False

def getFurthestSquare(adjLi, currPos, board, data):
    reachableSquares = regularDFS(adjLi, currPos, [])
    bodyLi = listifyMyBody(data)
    for bodyPiece in bodyLi[::-1]:
        for square in reachableSquares:
            if areAdjacent(bodyPiece, square):
                return square
        #first one that works is one I want
    #get list of all reachable squares with basic dfs
    #go through body and number it in dict key = (x,y) body, value = position in body
    #make another dict  whwere key=(x,y) space, value= sum of position of body pieces
    #return one with maximum value

ITERATIONS = 15
#TODO make it so tries to be near food and protects it
#XXX
def stallForTime(adjLi, currPos, board, data, bestMeal=None):
    global ITERATIONS
    """makes the snake move around in a way that will best maximize 
    the space it takes up, will chase its tail if it can,
    otherwise take the path that will maximize space taken up

    Arguments:\n
        adjLi {dict} -- the adjacency list
        currPos {tuple} -- the x,y coordinate of the snake head
        data {nested dictionary} -- all the game data

    Returns:
        move_response -- the direction that will best stall for time
    """

    ouroborous = pathToThing(adjLi, currPos, tailPos(data))
    if ouroborous != -1 and len(ouroborous) > 1:# and ouroborousIsSafe(adjLi, ouroborous, board):
        return dirToAdj(currPos, ouroborous[1])
    #if past this there is no path to tail
    targetSquare = getFurthestSquare(adjLi, currPos, board, data)
    #print("head is", currPos, "furthest square is", targetSquare)
    if targetSquare == currPos:#if already in that spot
        targetSquare = None
    
    path = longestDfs(adjLi, currPos, ITERATIONS, targetSquare)
    print("longest dfs success")
    if len(path) == 1:
        return errMove()
    return dirToAdj(currPos,path[1])

def noAvailableEnemies(adjLi, currPos):
    return pathToThing(adjLi, currPos, HEAD) == -1

def longestDfs(adjLi, currPos, iterations, targetSquare):
    """finds a decently long path from currPos, 
    ends if is no longer continuous
    
    Arguments:\n
        adjLi {dict} -- the adjacency list for the positioning.
        currPos {tuple} -- the x,y coordinate of the snake head.
        iterations {int} -- how many times it should look around for a new path.
    
    Returns:
        list of tuples -- the longest path it could find, starting at the head.
    """
    global DFSLen
    max = [None,0]
    for _ in range(iterations):
        DFSLen = None
        curr = DFS(adjLi, currPos, targetSquare, [])
        if DFSLen > max[1]:
            max = [curr, DFSLen]
    return max[0]

DFSLen = None

def DFS(adjLi, currPos, targetSquare, visited):
    """performs depth first search, choosing randomly from given options
        note that when backs out for first time the search stops
    
    Arguments:\n
        adjLi {dicitonary} -- the adjacency list.
        currPos {tuple} -- the x,y coordinates of the start of dfs.
    
    Keyword Arguments:\n
        visited {list} -- list of visited nodes.
    
    Returns:
        list of tuples -- sequence of nodes from currPos to end
    """
    global DFSLen

    if DFSLen is not None:#path that will be used is already done
        return

    visited.append(currPos)

    if currPos == targetSquare:#got to destination
        DFSLen = len(visited)
        return visited
        
    options = copy.deepcopy(adjLi[currPos][0])
    random.shuffle(options)

    for adj in options:
        if adj in visited:
            continue
        DFS(adjLi, adj, targetSquare, visited)
    
    if DFSLen is None:
        DFSLen = len(visited)
    return visited
        
#TODO make it more efficient
def getCorners(pos):
    """gets all positions in a square around a given position

    Arguments:\n
        pos {tuple} -- the x,y coordinates of a node

    Returns:
        list of tuples-- the positions in the "strike zone"
    """
    arr = []
    xStart = pos[0]
    yStart = pos[1]
    for x in range(xStart-2, xStart+3):
        for y in range(yStart-2, yStart+3):
            arr.append((x,y))

    for x in range(xStart-1, xStart+2):
        for y in range(yStart-1, yStart+2):
            arr.remove((x,y))
    return arr

#XXX replace this with better option?
def safetyRating(square, adjLi):
    if square not in adjLi:
        return None
    score = 0
    for neighbor in adjLi[square][0]:
        score += adjLi[neighbor][2]
    return score

def getSafestOption(sqA, ratingA, sqB, ratingB, adjLi):
    if ratingA is None and ratingB is None:
        return None

    if ratingA is None:
        return sqB
    if ratingB is None:
        return sqA
    
    if ratingA < ratingB:
        return sqA
    return sqB
    #result = sqA if ratingA < ratingB else sqB
    #return result

CW_DICT = {(-2,-1):(-2,0), (-2,0):(-2,1),
(-2,1):(-2, 2), (-2, 2):(-1, 2), (-1,2):(0,2),
(0,2):(1,2), (1,2):(2,2), (2,2):(2,1), (2,1):(2,0),
(2,0):(2,-1), (2,-1):(2,-2), (2,-2):(1,-2), (1,-2):(0,-2),
(0,-2):(-1,-2), (-1,-2):(-2,-2), (-2,-2):(-2,-1)}

CCW_DICT = {(-2, 0):(-2, -1), (-2, 1):(-2, 0),
(-2, 2):(-2, 1), (-1, 2):(-2, 2), (0, 2):(-1, 2),
(1, 2):(0, 2), (2, 2):(1, 2), (2, 1):(2, 2), (2, 0):(2, 1),
(2, -1):(2, 0), (2,-2):(2, -1), (1, -2):(2, -2), (0, -2):(1, -2),
(-1, -2):(0, -2),(-2, -2):(-1, -2), (-2, -1):(-2, -2)}

#true is clockwise
def rotateAttack(currPos, enemyHead, rotateDir=True, returnMove=True):
    global CW_DICT, CCW_DICT
    posDiff = (currPos[0]-enemyHead[0], currPos[1]-enemyHead[1])

    newDiff =CW_DICT[posDiff] if rotateDir else CCW_DICT[posDiff]
    if returnMove:
        return dirToAdj(currPos, (newDiff[0]+enemyHead[0], newDiff[1]+enemyHead[1]))
    else:
        return (newDiff[0]+enemyHead[0], newDiff[1]+enemyHead[1])

def clockwiseSquare(currPos, enemyHead, board):
    return rotateAttack(currPos, enemyHead, True, False)

def counterclockwiseSquare(currPos, enemyHead, board):
    return rotateAttack(currPos, enemyHead, False, False)

def safeDir(currPos, enemyHead, board, adjLi):
    cwSquare = clockwiseSquare(currPos, enemyHead, board)
    cwRating = safetyRating(cwSquare, adjLi)

    ccwSquare = counterclockwiseSquare(currPos, enemyHead, board)
    ccwRating = safetyRating(ccwSquare, adjLi)

    bestOption = getSafestOption(cwSquare, cwRating, ccwSquare, ccwRating, adjLi)
    if bestOption is None:
        return None#nowhere is safe
    else:
        return bestOption

#TODO figure out how to pick best side, maybe take average of DFS
#at each possibility, pick longest one
def sideBlock(currPos, enemyHead, adjLi, board, data):
    safeSpace = safeDir(currPos, enemyHead, board, adjLi)
    if safeSpace is not None:
        return dirToAdj(currPos, safeSpace)
    else:
        return stallForTime(adjLi, currPos, board, data) 

def errMove():
    """for when there is no good option
    
    Returns:
        move_response("up")
    """
    return move_response("up")

def attackProtocol(adjLi, currPos, board, data):
    """
        WIP
    """
    #print("FOR BLOOD, FOR GLORY")
    pathToVictim = pathToThing(adjLi, currPos, HEAD)
    victimHead = None
    if pathToVictim == -1:
        #print("NO PATH TO VICTIM")
        return stallForTime(adjLi, currPos, board, data)
    else:#if no victim in range
        victimHead = pathToVictim[-1]
    
    shortestPath = None
    for corner in getCorners(victimHead):
        pathToCorner = pathToThing(adjLi, currPos, corner)
        if pathToCorner == -1:
            continue
        if shortestPath is None or len(pathToCorner) < len(shortestPath):
            shortestPath = pathToCorner

    if shortestPath is None:
        #print("cant get to victim corner")
        return stallForTime(adjLi, currPos, board, data)
    if len(shortestPath) == 1:
        print("in the right spot", currPos)
        #showArr(board)
        return sideBlock(currPos, victimHead, adjLi, board, data)
    else:
        #print("going that way")
        return dirToAdj(currPos, shortestPath[1])#go to that square

#should take some stuff from getFoodPaths()
def dijkRetrace(start, food, dijkTable):
    curr = (food["x"], food["y"])
    if curr not in dijkTable:
        return None
    path=[dijkTable[curr][0], curr]
    for _ in range(len(dijkTable)):#is practically infinite loop
        #if curr not in dijkTable:
        #    print("dijkAYAYA", "head at",start, "food at", food, dijkTable)

        curr = dijkTable[curr][1]
        path.insert(1, curr)
        if curr == start:
            return path

def getFoodPaths(dijkTable, adjLi, data, head):
    allPaths = []
    for food in data["board"]["food"]:
        error=False
        curr = (food["x"], food["y"])
        path=dijkRetrace(head, food, dijkTable)
        if path is not None:
            allPaths.append(path)
    return sorted(allPaths, key=lambda path:path[0])

def mindex(ratios):
    min=math.inf
    minDex = None
    for i, ratio in enumerate(ratios):
        if ratio < min:
            min = ratio
            minDex = i
    return minDex

def determineBestMeal(adjLi, allFoodPaths, currHp, bodyLen, board, data):
    #return allFoodPaths[0]#works better
    allFoodPaths = [path for path in allFoodPaths if len(path)-1 >= currHp-bodyLen]
    #print("all foods is", allFoodPaths)
    #justPaths = [path[1:] for path in allFoodPaths]
    #nonSuicidal = [path for path in justPaths if not isSuicide(adjLi, path, board, data)]
    
    minRatio = 0
    minPath = None
    for i, path in enumerate(allFoodPaths):
        justPath = path[1:]
        futurePosition = possibleAdj(adjLi, board, justPath, data)
        reachableSquares = regularDFS(futurePosition, path[-1], [])
        ratio = len(reachableSquares)/path[0]
        if ratio > minRatio:
            minRatio = ratio
            minPath = path
    #maybe check number of all reachable squares and take ratio of 
    if len(allFoodPaths) > 0:
        return minPath
    else:
        return None
    
    '''if len(nonSuicidal) > 0:
        return nonSuicidal[0]#remember that sorted by weighted sums
    else:
        return None'''

'''{"game":{"id":"8481f485-029f-4ca7-82d3-3345bc70d76b"},"turn":7,"board":{"height":15,"width":15,"food":[{"x":11,"y":2},{"x":6,"y":8},{"x":5,"y":11},{"x":1,"y":3},{"x":7,"y":13},{"x":14,"y":11},{"x":10,"y":7},{"x":14,"y":13},{"x":1,"y":6},{"x":7,"y":14}],"snakes":[{"id":"c2e6e057-bea2-496e-8e4c-7b213117452d","name":"me","health":93,"body":[{"x":9,"y":3},{"x":8,"y":3},{"x":7,"y":3}]}]},"you":{"id":"540630d1-29e9-477a-9ab7-518222bf85f8","name":"you","health":93,"body":[{"x":15,"y":1},{"x":14,"y":1},
{"x":13,"y":1}]}}'''
#engine.exe dev
#python app\main.py
#http://0.0.0.0:8090/


#general TODO
'''
find a better way to find path to food and other things
find way to keep snake in strike zone and find best path to do so
'''

@bottle.post('/move')
def move():
    data = bottle.request.json
    currHp = data["you"]["health"]
    currPos = headPos(data)
    bodyLen = selfLength(data)

    board = makeBoard(data)
    adjLi = makeAdjList(board)
    makeWeightedAdj(adjLi, data)
    dijkTable = makeDijk(adjLi, currPos)
    
    allFoodPaths = getFoodPaths(dijkTable, adjLi, data, currPos)
    if len(allFoodPaths) == 0:#no path to food
        if noAvailableEnemies(adjLi, currPos):#no nearby enemies
            return stallForTime(adjLi, currPos, board, data)
        else:#are nearby enemies
            return attackProtocol(adjLi, currPos, board, data)

    #if here there is a food path
    #determine best meal is messing with list
    bestMeal = determineBestMeal(adjLi, allFoodPaths, currHp, bodyLen, board, data)
    if snakeIsHungry(bestMeal, currHp, bodyLen):
        return dirToAdj(currPos, bestMeal[2])#0 is value, 1 is head

    if noEnemies(data):
        stallForTime(adjLi, currPos, board, data)

    #if here snake isnt hungry and ready to wreck some fools
    return attackProtocol(adjLi, currPos, board, data)

    #showArr(board)
    #print(json.dumps(data))

    '''directions = ['up', 'down', 'left', 'right']
    direction = "up"
    return move_response(direction)'''


@bottle.post('/end')
def end():
    #data = bottle.request.json

    return end_response()

# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()

if __name__ == '__main__':
    bottle.run(
        application,
        host=os.getenv('IP', '0.0.0.0'),
        port=os.getenv('PORT', '8090'),
        debug=os.getenv('DEBUG', True)
    )
