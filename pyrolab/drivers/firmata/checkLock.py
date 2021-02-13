import asyncio
import websockets

async def hello(websocket, path):
    name = await websocket.recv()
    print(name)
    if name == "lock":
        await websocket.send("LOCKED")
    elif name == "unlock":
        await websocket.send("UNLOCKED")
    else:
        await websocket.send("Good to meet you " + name)

start_server = websockets.serve(hello, "localhost", 80)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()