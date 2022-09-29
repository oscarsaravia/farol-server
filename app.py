from aiohttp import web
import socketio
import uuid
import random
import os

## creates a new Async Socket IO Server
# sio = socketio.AsyncServer()
sio = socketio.AsyncServer(cors_allowed_origins='*')
## Creates a new Aiohttp Web Application
app = web.Application()
# Binds our Socket.IO server to our Web App
## instance
sio.attach(app)

## we can define aiohttp endpoints just as we normally
## would with no change
async def index(request):
    with open('index.html') as f:
        return web.Response(text=f.read(), content_type='text/html')


cards = ['CLUB_A', 'CLUB_2', 'CLUB_3', 'CLUB_4', 'CLUB_5', 'CLUB_6', 'CLUB_7', 'CLUB_8', 'CLUB_9', 'CLUB_10', 'CLUB_J', 'CLUB_Q', 'CLUB_K', 'DIAMOND_A', 'DIAMOND_2', 'DIAMOND_3', 'DIAMOND_4', 'DIAMOND_5', 'DIAMOND_6', 'DIAMOND_7', 'DIAMOND_8', 'DIAMOND_9', 'DIAMOND_10', 'DIAMOND_J', 'DIAMOND_Q', 'DIAMOND_K', 'HEART_A', 'HEART_2', 'HEART_3', 'HEART_4', 'HEART_5', 'HEART_6', 'HEART_7', 'HEART_8', 'HEART_9', 'HEART_10', 'HEART_J', 'HEART_Q', 'HEART_K', 'SPADE_A', 'SPADE_2', 'SPADE_3', 'SPADE_4', 'SPADE_5', 'SPADE_6', 'SPADE_7', 'SPADE_8', 'SPADE_9', 'SPADE_10', 'SPADE_J', 'SPADE_Q', 'SPADE_K', 'JOKER_1', 'JOKER_2', 'JOKER_3']
rooms = {}
play_cards = ['_A', '_2', '_3', '_4', '_5', '_6', '_7', '_8', '_9', '_10', '_J', '_Q', '_K']

'''
  @param username
  @return {
    response,
    code,
    body: {
      room_id string,
      owner string
    }
  }
'''
@sio.on('create_room')
async def join_room(_, username):
  room_id = str(uuid.uuid1())
  rooms[room_id] = {
    "id": room_id,
    "stack": [],
    "players": {
        "owner": {
            "username": username,
            "cards": [],
        }
    }
  }
  print("Created room: " , room_id)
  await sio.emit('room_created', {
    "response": "room_created",
    "code": 200,
    "body": {
      "room_id": room_id,
      "owner": username,
    }
  })

'''
  @param room_id string
  @param username string
  @return {
    response,
    code,
    body: {
      owner: string,
      room_id: string,
      players: []
    }
  }
'''
@sio.on('join_room')
async def join_room(_, room_id, username):
  able_to_join = len(rooms[room_id]['players']) < 4
  if able_to_join:
    rooms[room_id]['players'][username] = {
      "username": username,
      "cards": [],
    }

    print(username, " Joined room: " , room_id)
    await sio.emit('joined_room', {
      "response": "joined_room",
      "code": 200,
      "body": {
        "room_id": room_id,
        "owner": rooms[room_id]['players']['owner']['username'],
        "players": rooms[room_id]['players'],
      }
    })
  else:
    print("Room is full", username, " Tried to join room: " , room_id)
    await sio.emit('room_full', {
      "response": "room_full",
      "code": 101,
    })

'''
  @param room_id string
  @return {
    response,
    code,
    body: {
      players: [{
        username: string,
        position: number,
        cards: strings[]
      }],
      next_player: string,
      next_card string
    }
  }
'''
@sio.on('start_game')
async def start_game(_, room_id):
    player_count = len(rooms[room_id]['players'])
    new_cards = cards.copy()
    random.shuffle(new_cards)
    players = list(rooms[room_id]['players'].keys())
    random.shuffle(players)

    for i in range(len(new_cards)):
        player_pos = i%player_count
        rooms[room_id]['players'][players[player_pos]]['cards'].append(new_cards[i])

    for i in range(len(players)):
        rooms[room_id]['players'][players[i]]['position'] = i

    rooms[room_id]['messages'] = []

    # add the card to the actual_card
    rooms[room_id]['actual_card'] = '_A'


    print("Game started in room: " , room_id, rooms[room_id]['players'])
    await sio.emit('game_started', {
        "response": "game_started",
        "code": 200,
        "body": {
            "players": rooms[room_id]['players'],
            "next_player": players[0],
            "next_card": rooms[room_id]['actual_card'],
        }
    })

'''
  @param card string
  @param room_id string
  @param username string
  @return {
    response,
    code,
    body: {
      next_player: string,
      last_player: string,
      next_card: string,
      players: [{
        username: string,
        position: number,
        cards: strings[]
    }
  }
'''
@sio.on('next_turn')
async def next_turn(_, card, room_id, username):
    # add the card to the stack
    rooms[room_id]['stack'].append(card)

    actual_player = rooms[room_id]['players'][username]['position']
    next_player = (actual_player + 1) % len(rooms[room_id]['players'])
    next_player_username = ''
    # remove the card from the player
    rooms[room_id]['players'][username]['cards'].remove(card)
    # find the next player
    for player in rooms[room_id]['players']:
        if rooms[room_id]['players'][player]['position'] == next_player:
            next_player_username = player

    # find the next card to play
    next_card = ''
    for card in play_cards:
        if card == rooms[room_id]['actual_card']:
            next_card = play_cards[(play_cards.index(card) + 1) % len(play_cards)]
            rooms[room_id]['actual_card'] = next_card
            break


    print("Next turn is for: ", next_player_username, " in room: " , room_id, 'current stack: ', rooms[room_id]['stack'])
    await sio.emit('next_turn', {
        "response": "next_turn",
        "code": 200,
        "body": {
            "next_player": next_player_username,
			      "last_player": username,
            "players": rooms[room_id]['players'],
            "next_card": next_card,
        }
    })

'''
  @param telltale string
  @param accused string
  @param room_id string
  @return {
    response,
    code,
    body: {
      answer: boolean,
      telltale: string,
      accused: string,
      players: [{
        username: string,
        position: number,
        cards: strings[]
      }]
      room_id: string,
    }
  }
'''
@sio.on('farol')
async def farol(_, telltale, accused, room_id):
    last_card_in_stack = rooms[room_id]['stack'][-1]
    index_last_card = (play_cards.index(rooms[room_id]['actual_card']) - 1) % len(play_cards)
    last_card = play_cards[index_last_card]
    answer = last_card not in last_card_in_stack and 'JOKER' not in last_card_in_stack

    cards = rooms[room_id]['stack'].copy()
    rooms[room_id]['stack'] = []

    # if answer is true, the accused player loses
    if answer:
        for card in cards:
            rooms[room_id]['players'][accused]['cards'].append(card)
    else:
        for card in cards:
            rooms[room_id]['players'][telltale]['cards'].append(card)

    print("Telltale: ", telltale, " was " , answer, 'to accused', accused, cards)
    await sio.emit('farol', {
        "response": "farol",
        "code": 200,
        "body": {
            "answer": answer,
            "telltale": telltale,
            "accused": accused,
            "players": rooms[room_id]['players'],
            "room_id": room_id,
        }
    })

'''
  @param winner string
  @param room_id string
  @return {
    response,
    code,
    body: {
      winner: string,
      room_id: string,
    }
  }
'''
@sio.on('finish_game')
async def finis_game(_, winner, room_id):
    # remove the room if it exists
    if room_id in rooms:
        del rooms[room_id]
    print("Game finished in room: " , room_id, " Winner: ", winner)
    await sio.emit('game_finished', {
        "response": "game_finished",
        "code": 200,
        "body": {
            "winner": winner,
            "room_id": room_id,
        }
    })

'''
  @param username string
  @param room_id string
  @param message string
  @return {
    response,
    code,
    body: {
      chat: [{
        username: string,
        message: string,
      }],
      room_id: string
    }
  }
'''
@sio.on('send_message')
async def send_message(_, username, room_id, message):
    message = {
        "username": username,
        "message": message,
    }
    rooms[room_id]['messages'].append(message)

    print("New message from:" , username, "message: ", message, " in room: " , room_id)
    await sio.emit('message_recieved', {
        "response": "message_recieved",
        "code": 200,
        "body": {
            "room_id": room_id,
            "chat": rooms[room_id]['messages'],
        }
    })

## We bind our aiohttp endpoint to our app
## router
app.router.add_get('/', index)

## We kick off our server
if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=os.environ.get('PORT', '5000'))