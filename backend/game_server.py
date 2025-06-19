# game_server.py
# Updated to stream image generation progress to all clients in a room.

import asyncio
import websockets
import json
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional

# --- Configuration & Prompts (No changes here) ---
AI_SERVER_URI = "ws://localhost:8000/ws/generate"
GAME_CONFIG = {
    "ROUND_DURATION_S": 30,
    "POST_ROUND_DELAY_S": 10,
    "MAX_PLAYERS": 12,
    "POINTS_FOR_CORRECT_GUESS": 1000
}
PROMPTS = [
    "A photorealistic portrait of a cat wearing a monocle",
    "A squirrel in the style of picasso",
    "Darth vader playing the drums",
    "An astronaut playing guitar on the moon",
    "Yoda playing the guitar",
    "An image of a crow sitting in a tree",
    "very long limo",
    "happy software developer",
    "pug pikachu"
    "a boat on a river"
]

# --- GameRoom Class (Main Changes are Here) ---

class GameRoom:
    """Manages the state and logic for a single game room."""

    def __init__(self, room_id: str):
        self.room_id: str = room_id
        self.host: Optional[str] = None
        self.players: Dict[str, WebSocket] = {}
        self.scores: Dict[str, int] = {}
        self.game_state: str = "LOBBY"
        self.current_prompt: str = ""
        self.current_image_b64: Optional[str] = ""
        self.round_timer_task: Optional[asyncio.Task] = None
        self.game_loop_task: Optional[asyncio.Task] = None
        # NEW: Add a task for the image generation stream
        self.image_stream_task: Optional[asyncio.Task] = None
        print(f"Room {room_id} created.")

    # --- Connection Management & Message Handling (No changes here) ---
    async def connect(self, websocket: WebSocket, player_name: str):
        await websocket.accept()
        self.players[player_name] = websocket
        self.scores[player_name] = 0
        if self.host is None:
            self.host = player_name
        await self.broadcast_player_update()
        print(f"Player '{player_name}' connected to room '{self.room_id}'. Host is '{self.host}'.")

    async def disconnect(self, player_name: str):
        if player_name in self.players:
            del self.players[player_name]
            del self.scores[player_name]
            if self.host == player_name:
                self.host = next(iter(self.players), None)
            if not self.players and self.game_loop_task:
                 self.game_loop_task.cancel()
                 if self.image_stream_task:
                    self.image_stream_task.cancel()
            await self.broadcast_player_update()
            print(f"Player '{player_name}' disconnected. New host is '{self.host}'.")

    async def broadcast(self, message: dict):
        if not self.players: return
        await asyncio.gather(
            *[player.send_json(message) for player in self.players.values()],
            return_exceptions=False
        )

    async def broadcast_player_update(self):
        player_data = [
            {"name": name, "score": self.scores[name], "isHost": name == self.host}
            for name in self.players
        ]
        await self.broadcast({"type": "player_update", "payload": {"players": player_data}})

    async def handle_message(self, player_name: str, data: dict):
        message_type = data.get("type")
        payload = data.get("payload", {})
        if message_type == "start_game" and player_name == self.host:
            await self.start_game()
        elif message_type == "new_guess":
            await self.process_guess(player_name, payload.get("guess"))

    # --- Game Logic (CHANGED) ---

    async def start_game(self):
        if self.game_state == "LOBBY":
            self.game_state = "IN_GAME"
            print(f"Room '{self.room_id}' is starting the game.")
            await self.broadcast({"type": "game_started", "payload": {}})
            self.game_loop_task = asyncio.create_task(self.run_game_loop())

    async def run_game_loop(self):
        for round_num in range(1, len(PROMPTS) + 1):
            if not self.players:
                break
            await self.start_round(round_num)
            await asyncio.sleep(GAME_CONFIG["ROUND_DURATION_S"] + GAME_CONFIG["POST_ROUND_DELAY_S"])
        
        print(f"Game in room '{self.room_id}' has ended.")
        self.game_state = "LOBBY"

    async def start_round(self, round_num: int):
        """Initializes a round, sends initial data, THEN starts the image stream."""
        self.current_prompt = random.choice(PROMPTS)
        print(f"Room '{self.room_id}' Round {round_num}: Prompt is '{self.current_prompt}'")

        # Step 1: Broadcast the new turn signal with a NULL image initially.
        # This tells the UI to get ready for the stream.
        await self.broadcast({
            "type": "new_turn",
            "payload": {
                "round": round_num,
                "totalRounds": len(PROMPTS),
                "timeLeft": GAME_CONFIG["ROUND_DURATION_S"],
                "imageBase64": None, # Initially null
                "promptHint": f"{len(self.current_prompt.split())} words"
            }
        })
        
        # Step 2: Start the background tasks for the timer AND the image stream
        if self.round_timer_task: self.round_timer_task.cancel()
        if self.image_stream_task: self.image_stream_task.cancel()
        
        self.round_timer_task = asyncio.create_task(self.round_timer())
        self.image_stream_task = asyncio.create_task(self.run_image_generation_and_broadcast())

    async def run_image_generation_and_broadcast(self):
        """Connects to AI server and broadcasts each image chunk as it arrives."""
        try:
            async with websockets.connect(AI_SERVER_URI) as ai_websocket:
                await ai_websocket.send(self.current_prompt)
                
                while True:
                    message = await ai_websocket.recv()
                    
                    if message == "generation_complete":
                        print(f"Room '{self.room_id}': Generation complete.")
                        break # End this task
                    
                    # We received an image chunk. Broadcast it immediately.
                    self.current_image_b64 = message # Keep track of the latest image
                    full_data_url = f"data:image/png;base64,{self.current_image_b64}"
                    # Convert the image chunk to base64
                    await self.broadcast({
                        "type": "image_update",
                        "payload": {"imageBase64": full_data_url}
                    })

        except Exception as e:
            print(f"Room '{self.room_id}': Error during image generation stream: {e}")

    async def round_timer(self):
        await asyncio.sleep(GAME_CONFIG["ROUND_DURATION_S"])
        if self.game_state == "IN_GAME":
            print(f"Room '{self.room_id}' timer expired.")
            await self.end_round(winner=None, reason="Time is up!")

    async def process_guess(self, player_name: str, guess: str):
        if not guess: return
        await self.broadcast({
            "type": "new_guess",
            "payload": {"player": player_name, "message": guess}
        })
        if guess.strip().lower() == self.current_prompt.lower():
            self.scores[player_name] += GAME_CONFIG["POINTS_FOR_CORRECT_GUESS"]
            await self.end_round(winner=player_name, reason=f"Guessed correctly!")

    async def end_round(self, winner: Optional[str], reason: str):
        # Stop all background tasks for this round
        if self.round_timer_task: self.round_timer_task.cancel()
        if self.image_stream_task: self.image_stream_task.cancel()

        self.game_state = "POST_ROUND"
        print(f"Room '{self.room_id}' round ended. Winner: {winner}. Reason: {reason}")
        await self.broadcast({
            "type": "round_end",
            "payload": {
                "correctPrompt": self.current_prompt,
                "winner": winner,
                "reason": reason,
                "scores": [{"name": name, "score": self.scores[name]} for name in self.players]
            }
        })

# --- ConnectionManager and FastAPI App (No changes here) ---
class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, GameRoom] = {}
    def get_or_create_room(self, room_id: str) -> GameRoom:
        if room_id not in self.rooms:
            self.rooms[room_id] = GameRoom(room_id)
        return self.rooms[room_id]
    def remove_room_if_empty(self, room_id: str):
        if room_id in self.rooms and not self.rooms[room_id].players:
            del self.rooms[room_id]
            print(f"Room '{room_id}' is empty and has been closed.")

app = FastAPI()
manager = ConnectionManager()

@app.websocket("/ws/game/{room_id}/{player_name}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, player_name: str):
    room = manager.get_or_create_room(room_id)
    if len(room.players) >= GAME_CONFIG["MAX_PLAYERS"] or player_name in room.players:
        await websocket.accept()
        await websocket.close(code=1008, reason="Room is full or name is taken.")
        return
    await room.connect(websocket, player_name)
    try:
        while True:
            data = await websocket.receive_json()
            await room.handle_message(player_name, data)
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for player '{player_name}' in room '{room_id}'.")
    finally:
        await room.disconnect(player_name)
        manager.remove_room_if_empty(room_id)