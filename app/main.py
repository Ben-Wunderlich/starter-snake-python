import json
import os
import random
import bottle

from api import ping_response, start_response, move_response, end_response

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
    arr = []
    for _ in range(height):
        arr.append([])
        for _ in range(width):
            arr[-1].append(0)
    return arr

"""
0 = empty space
1 = food
2 = my body
3 = other snake bodies
4 = other snake heads
"""
SPACE = 0
FOOD = 1
MYHEAD = 2
SELF = 3
BODY = 4
HEAD = 5

def makeBoard(data):
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

        for part in snake["body"][1:]:
            if isSelf:
                arr[part["y"]][part["x"]] = SELF
            else:
                arr[part["y"]][part["x"]] = BODY
    
    #showArr(arr)
    return arr

def showArr(arr):
    for line in arr:
        for char in line:
            if char == 0:
                print("0 ", end="")

            else:
                print(char,"", end="")
        print()

def headPos(data):
    headTemp = data["you"]["body"][0]
    return (headTemp["x"],headTemp["y"])

def noEnemies(data):
    return len(data["board"]["snakes"])-1 == 0

def noFood(data):
    return len(data["board"]["food"]) == 0

def ouroboros(board):
    pass

def getFoodPos(data):
    return data["board"]["food"]

def retracePath(parents, adjNode, start):
    path=[adjNode]
    v = adjNode
    while v != start:
        v = parents[v]
        path.insert(0, v)
    return path

def isSuicide(path, adjLi):
    pass

#gives shortest path to nearest food
def getFood(adjLi, data, headPos):
    visitQueue = [headPos]
    parents = {}
    while visitQueue: #is false only if empty
        baseKey = visitQueue.pop()
        for adjNode in adjLi[baseKey][0]:
            if adjNode not in parents.keys(): #if undiscovered
                parents[adjNode] = baseKey #mark parent relationship
                if adjLi[adjNode][1] == FOOD:
                    path = retracePath(parents, adjNode, headPos)
                    if not isSuicide(path, adjLi):
                        return dirToAdj(headPos, path[1])
                    #else just keeps going
                visitQueue.insert(0, adjNode)
    print("couldnt find food")
    return move_response("up")

def dirToAdj(head, adj):
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

def shortestPath(start, end, board):
    pass

def isStarving(data):
    return data["you"]["health"] <= STARVING

def getAdjNodes(board, x, y):
    adj = []
    if x > 0 and board[y][x-1] < SELF:
        adj.append((x-1, y))
    if y > 0 and board[y-1][x] < SELF:
        adj.append((x, y-1))
    return adj

def makeAdjList(board):
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

def foodInRange(data):
    pass


'''{"game":{"id":"8481f485-029f-4ca7-82d3-3345bc70d76b"},"turn":7,"board":{"height":15,"width":15,"food":[{"x":11,"y":2},{"x":6,"y":8},{"x":5,"y":11},{"x":1,"y":3},{"x":7,"y":13},{"x":14,"y":11},{"x":10,"y":7},{"x":14,"y":13},{"x":1,"y":6},{"x":7,"y":14}],"snakes":[{"id":"c2e6e057-bea2-496e-8e4c-7b213117452d","name":"me","health":93,"body":[{"x":9,"y":3},{"x":8,"y":3},{"x":7,"y":3}]}]},"you":{"id":"540630d1-29e9-477a-9ab7-518222bf85f8","name":"you","health":93,"body":[{"x":15,"y":1},{"x":14,"y":1},
{"x":13,"y":1}]}}'''
#engine.exe dev
#python app\main.py
#http://0.0.0.0:8088/

STARVING = 5
PERSONAL_SPACE = 3

@bottle.post('/move')
def move():
    data = bottle.request.json
    currHp = data["you"]["health"]
    #print("currhp is", currHp)
    currPos = headPos(data)
    """
    TODO: Using the data from the endpoint request object, your
            snake AI must choose a direction to move in.
    """
    board = makeBoard(data)
    adjList = makeAdjList(board)

    if noEnemies(data):
        if noFood(data):
            return ouroboros(board)#circle itself
        else:
            return getFood(adjList, data, currPos)
    
    else:
        if isStarving(data):
            if foodInRange(data):
                return getFood(adjList, data, currPos)
        print("there are enemie")

    
    #if here is an enemy

    
        
    #showArr(board)
    #print(adjList)
    #print(json.dumps(data))

    directions = ['up', 'down', 'left', 'right']
    #direction = random.choice(directions)
    direction = "right"
    return move_response(direction)


@bottle.post('/end')
def end():
    data = bottle.request.json

    """
    TODO: If your snake AI was stateful,
        clean up any stateful objects here.
    """
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
