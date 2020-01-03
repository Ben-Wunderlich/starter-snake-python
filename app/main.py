import json
import os
import random
import bottle

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

TOO_CLOSE = 3

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

    """
    TODO: If you intend to have a stateful snake AI,
            initialize your snake state here using the
            request's data if necessary.
    """
    print(json.dumps(data))

    color = "#00FFFF"

    return start_response(color)

def initBoard(height, width):
    """creates an empty board(filled with 0's)
    
    Arguments:
        height {int} -- the height of the board
        width {int} -- the width of the board
    
    Returns:
        list of lists -- the empty board
    """
    arr = []
    for _ in range(height):
        arr.append([])
        for _ in range(width):
            arr[-1].append(0)
    return arr

def makeBoard(data):
    """creates a board to model what is going on in the game
    
    Arguments:
        data {dictionary} -- the game information
    
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

        for part in snake["body"][1:-1]:#-1 so doesnt count tail
            if isSelf:
                arr[part["y"]][part["x"]] = SELF
            else:
                arr[part["y"]][part["x"]] = BODY
    
    #showArr(arr)
    return arr

def showArr(arr):
    """shows an array, for debugging ONLY
    
    Arguments:
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
    
    Arguments:
        data {dictionary} -- the game data
    
    Returns:
        tuple -- x,y coordinates of the head
    """
    headTemp = data["you"]["body"][0]
    return (headTemp["x"],headTemp["y"])

def noEnemies(data):
    """checks if there are any enemies on the board
    
    Arguments:
        data {dictionary} -- the game data
    
    Returns:
        boolean -- true if no other snakes around, else false
    """
    return len(data["board"]["snakes"])-1 == 0


def retracePath(parents, finalNode, start):
    """retraces path from destination to start
    
    Arguments:
        parents {dictionary} -- has [parent]:children relationships
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

#note that doesnt add in spaces that will no longer be self
def possibleLi(adjLi, path):
    """makes the adjacency list that would result from taken a given path
    note that doesnt remove parts of snake that are no longer there
    TODO remove tail of snake depending on length
    
    Arguments:
        adjLi {dictionary} -- the original ajacency list
        path {list of tuples} -- the list of x,y coordinates of nodes to be travelled
    
    Returns:
        dictionary -- the adjacency list if the path is taken
    """
    newLi = adjLi.copy()
    for nodeKey in path[:-1]:
        delAdjNode(newLi, nodeKey)
    #print("debugMe",newLi)
    return newLi


def isSuicide(adjLi, path):
    """checks if a given path would likely lead to premature snake death
    
    Arguments:
        adjLi {dictionary} -- the adjacency list
        path {list of tuples} -- nodes the snake would take
    
    Returns:
        boolean -- true if is probably suicide, else false
    """
    head = path[-1]
    adjLi[head][1] = MYHEAD#so doesnt find itself

    futureAdj = possibleLi(adjLi, path)
    minDist = pathToThing(futureAdj, path[-1], FOOD)
    if type(minDist) != int:
        minDist = len(minDist)
    
    adjLi[head][1] = FOOD#so doesnt find itself

    return minDist == -1 or minDist < TOO_CLOSE

def getFood(adjLi, headPos):
    """finds a path that would best find food for the snake without
    putting it into mortal danger
    
    Arguments:
        adjLi {dictionary} -- the adjacency list for possible moves
        headPos {tuple} -- the x,y coordinates of where the snake head is
    
    Returns:
        move_response -- the direction to move towards to best get food
    """
    visitQueue = [headPos]
    parents = {}
    aPath = False
    while visitQueue: #is false only if empty
        baseKey = visitQueue.pop()
        for adjNode in adjLi[baseKey][0]:
            if adjNode not in parents.keys(): #if undiscovered
                parents[adjNode] = baseKey #mark parent relationship
                if adjLi[adjNode][1] == FOOD:
                    aPath = True
                    path = retracePath(parents, adjNode, headPos)
                    if not isSuicide(adjLi, path):
                        return dirToAdj(headPos, path[1]) 
                    #else just keeps going
                visitQueue.insert(0, adjNode)
    if aPath:
        return -2
    return -1

def dirToAdj(head, adj):
    """finds the direction from one node to an adjacent one
    
    Arguments:
        head {tuple} -- the x,y coordinates of the node being looked from
        adj {tuple} -- the x,y coordinates of the node being looked towards
    
    Returns:
        string -- move_response that would get from head to adj
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

def getAdjNodes(board, x, y):
    """finds the adjacent nodes of a node
    
    Arguments:
        board {list of lists} -- the board on which the snakes are
        x {int} -- the x position of the square being checked
        y {int} -- the y position of the square being checked
    
    Returns:
        list of tuples -- the keys of adjacent nodes
    """
    adj = []
    if x > 0 and board[y][x-1] < SELF:
        adj.append((x-1, y))
    if y > 0 and board[y-1][x] < SELF:
        adj.append((x, y-1))
    return adj

def makeAdjList(board):
    """makes the adjacency list for possible squares the snake can traverse
    
    Arguments:
        board {list of lists} -- the board with values defining whats there
            see CONSTANTS at top of file for more info
    
    Returns:
        dictionary -- the adjacency list, with keys being x,y tuple coordinate
            of the square and value being a list
                [0] is list of adjacent nodes
                [1] is int identity of node, see top of file again
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
                adjLi[key] = [adjNodes, el]
    return adjLi

def makeSafeAdj(adjLi, data):
    """
        not currently functional and will probably be removed
    """
    safeAdj = adjLi.copy()
    for snake in data["board"]["snakes"]:
        if snake["id"] == data["you"]["id"]:
            continue
        snakeHead = snake["body"][0]
        xHead = snakeHead["x"]
        yHead = snakeHead["y"]
        for x in range(xHead-1, xHead+1):
            for y in range(yHead-1, yHead+1):
                delAdjNode(safeAdj, (x,y))
    return safeAdj

def delAdjNode(adjLi, delNode):
    """deletes a node and anything referenceing it from the adjacency list
    
    Arguments:
        adjLi {dictionary} -- the adjacency list
        delNode {tuple} -- the node to be deleted
    """
    if delNode not in adjLi.keys():
        return
    for connected in adjLi[delNode][0]:
        if delNode not in adjLi[connected][0]:
            continue
        adjLi[connected][0].remove(delNode)
    del adjLi[delNode]

def selfLength(data):
    """finds how long the snake is
    
    Arguments:
        data {dictionary} -- the game data
    
    Returns:
        int -- the snakes length
    """
    return len(data["you"]["body"])

def needsFoodNow(safeLi, currPos, currHp, bodyLength):
    """determines if the snake has enough time to make it to
    the nearest food
    
    Arguments:
        safeLi {dictionary} -- the adjacency list
        currPos {tuple} -- the x,y coordinate of the snakes head
        currHp {int} -- how much health the snake has remaining
        bodyLength {int} -- how long the snake is
    
    Returns:
        boolean -- True if is in danger of starvation, else False
    """
    path = pathToThing(safeLi, currPos, FOOD)
    if type(path) == int:
        return False
    return len(path) >= currHp-bodyLength

def tailPos(data):
    """gets the position of the tail of the snake
    
    Arguments:
        data {dictionary} -- the game data
    
    Returns:
        tuple -- x,y coordinate of the tail
    """
    tailSegment = data["you"]["body"][-1]
    return (tailSegment["x"], tailSegment["y"])

#can pass either int or tuple as target
def pathToThing(adjLi, headPos, target):
    """finds the shortest path to a target from the head position
    
    Arguments:
        adjLi {dictionary} -- the adjacency list
        headPos {tuple} -- the snake head position
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
                #assert(adjLi[adjNode][1] != HEAD)
                if adjNode == target or adjLi[adjNode][1] == target:
                    path = retracePath(parents, adjNode, headPos)
                    return path

                visitQueue.insert(0, adjNode)
    return -1


def stallForTime(adjLi, currPos, data):
    """makes the snake move around in a way that will best minimize 
    the space it takes up, will chase its tail if it can,
    otherwise take the path that will maximize space taken up

    Arguments:
        adjLi {dictionary} -- the adjacency list
        currPos {tuple} -- the x,y coordinate of the snake head
        data {nested dictionary} -- all the game data

    Returns:
        move_response -- the direction that will best stall for time
    """
    iterations = 15

    ouroborous = pathToThing(adjLi, currPos, tailPos(data))
    if ouroborous != -1:
        return dirToAdj(currPos, ouroborous[1])
    #if past this there is no path to tail
    
    path = longestDfs(adjLi, currPos, iterations)
    if len(path) == 1:
        return errMove()
    return dirToAdj(currPos,path[1])

def longestDfs(adjLi, currPos, iterations):
    """finds a decently long path from currPos, 
    ends if is no longer continuous
    
    Arguments:
        adjLi {dictionary} -- the adjacency list for the positioning
        currPos {tuple} -- the x,y coordinate of the snake head
        iterations {int} -- how many times it should look around for a new path
    
    Returns:
        list of tuples -- the longest path it could find, starting at the head
    """
    global DFSLen
    max = [None,0]
    for _ in range(iterations):
        DFSLen = None
        curr = DFS(adjLi, currPos)
        #print("dfsLen is", DFSLen)
        if DFSLen > max[1]:
            max = [curr, DFSLen]
    return max[0]

DFSLen = None

def DFS(adjLi, currPos, visited=None):
    """performs depth first search, choosing randomly from given options
        note that when backs out for first time the search stops
    
    Arguments:
        adjLi {dicitonary} -- the adjacency list
        currPos {tuple} -- the x,y coordinates of the start of dfs
    
    Keyword Arguments:
        visited {int or None} -- list of visited nodes (default: {None})
    
    Returns:
        list of tuples -- sequence of nodes from currPos to end
    """
    global DFSLen

    if DFSLen is not None:#path that will be used is already done
        return

    if visited is None:
        visited = [currPos]
    else:
        visited.append(currPos)
        
    options = adjLi[currPos][0].copy()
    random.shuffle(options)

    for adj in options:
        if adj in visited:
            continue
        DFS(adjLi, adj, visited)
    
    if DFSLen is None:
        DFSLen = len(visited)
    return visited
        
#TODO make it faster
def getCorners(pos):
    """gets all positions in a square around a given position

    Arguments:
        pos {tuple} -- pos[0] = x position || pos[1] = y position

    Returns:
        list of tuples-- the positions in the "strike zone"
    """
    arr = []
    xStart = pos[0]
    yStart = pos[1]
    for x in range(xStart-2, xStart+2):
        for y in range(yStart-2, yStart+2):
            arr.append((x,y))

    for x in range(xStart-1, xStart+1):
        for y in range(yStart-1, yStart+1):
            arr.remove((x,y))
    print("XQC", arr)
    return arr

#TODO figure out how to stay in head space and pick best side
def sideBlock(currPos, enemyHead, closestCorner, adjLi, board):
    print("sideblocking")
    return

def errMove():
    """for when there is no good options
    
    Returns:
        move_response("up")
    """
    return move_response("up")

def attackProtocol(adjLi, currPos, board, data):
    """
        WIP
    """
    pathToVictim = pathToThing(adjLi, currPos, HEAD)
    print("path is", pathToVictim)
    victimHead = None
    if pathToVictim == -1:
        return stallForTime(adjLi, currPos, data)
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
        return stallForTime(adjLi, currPos, data)

    closestCorner = shortestPath[-1]
    if currPos == closestCorner:
        return sideBlock(currPos, victimHead, closestCorner, adjLi, board)
    else:
        return dirToAdj(currPos, shortestPath[1])#go to that square


'''{"game":{"id":"8481f485-029f-4ca7-82d3-3345bc70d76b"},"turn":7,"board":{"height":15,"width":15,"food":[{"x":11,"y":2},{"x":6,"y":8},{"x":5,"y":11},{"x":1,"y":3},{"x":7,"y":13},{"x":14,"y":11},{"x":10,"y":7},{"x":14,"y":13},{"x":1,"y":6},{"x":7,"y":14}],"snakes":[{"id":"c2e6e057-bea2-496e-8e4c-7b213117452d","name":"me","health":93,"body":[{"x":9,"y":3},{"x":8,"y":3},{"x":7,"y":3}]}]},"you":{"id":"540630d1-29e9-477a-9ab7-518222bf85f8","name":"you","health":93,"body":[{"x":15,"y":1},{"x":14,"y":1},
{"x":13,"y":1}]}}'''
#engine.exe dev
#python app\main.py
#http://0.0.0.0:8088/

STARVING = 5
PERSONAL_SPACE = 3

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
    #safeLi = makeSafeAdj(adjLi, data)

    if needsFoodNow(adjLi, currPos, currHp, bodyLen):
        foodDir = getFood(adjLi, currPos)
        if foodDir == -1 or foodDir == -2:
            return stallForTime(adjLi, currPos, data)
        else:
            return foodDir

    if noEnemies(data):
        return stallForTime(adjLi, currPos, data)
    
    #if here then doesnt need food and enemies are around
    return attackProtocol(adjLi, currPos, board, data)

    #showArr(board)
    #print(adjList)
    #print(json.dumps(data))

    '''directions = ['up', 'down', 'left', 'right']
    direction = "up"
    print("you messed up bro")
    return move_response(direction)'''


@bottle.post('/end')
def end():
    data = bottle.request.json

    #print(json.dumps(data))

    return end_response()

# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()

if __name__ == '__main__':
    bottle.run(
        application,
        host=os.getenv('IP', '0.0.0.0'),
        port=os.getenv('PORT', '8088'),
        debug=os.getenv('DEBUG', True)
    )
