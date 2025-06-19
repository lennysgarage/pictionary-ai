# game_server.py
# This script is a full multiplayer game server for the Pictionary AI frontend.
# It manages game rooms, player state, and the game loop.
# It still acts as a client to the AI server to generate images.
# --- Dependencies ---
# pip install "fastapi[all]" uvicorn websockets Pillow

import asyncio
import websockets
import json
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional

# --- Configuration ---
AI_SERVER_URI = "ws://localhost:8000/ws/generate"

# --- Game Configuration ---
GAME_CONFIG = {
    "ROUND_DURATION_S": 60,
    "POST_ROUND_DELAY_S": 10,
    "MAX_PLAYERS": 8,
    "POINTS_FOR_CORRECT_GUESS": 500
}

# --- Game Content ---
# A list of prompts for the AI to generate. In a real app, this could come from a file or database.
PROMPTS = [
    "A photorealistic portrait of a cat wearing a monocle",
    "A robot painting a beautiful sunset",
    "A cosmic owl flying through a nebula",
    "A city skyline made of giant books",
    "An astronaut playing guitar on the moon",
    "A dragon drinking tea in a Japanese garden",
    "A steampunk submarine exploring the deep ocean",
    "A whimsical treehouse in an enchanted forest"
]

# --- Server State and Models ---

class GameRoom:
    """Manages the state and logic for a single game room."""

    def __init__(self, room_id: str):
        self.room_id: str = room_id
        self.host: Optional[str] = None
        self.players: Dict[str, WebSocket] = {}
        self.scores: Dict[str, int] = {}
        self.game_state: str = "LOBBY"  # LOBBY, IN_GAME, POST_ROUND
        self.current_prompt: Optional[str] = None
        self.current_image_b64: Optional[str] = None
        self.round_timer_task: Optional[asyncio.Task] = None
        self.game_loop_task: Optional[asyncio.Task] = None
        print(f"Room {room_id} created.")

    # --- Connection Management ---

    async def connect(self, websocket: WebSocket, player_name: str):
        """Adds a player to the room and notifies others."""
        await websocket.accept()
        self.players[player_name] = websocket
        self.scores[player_name] = 0
        if self.host is None:
            self.host = player_name
        
        # Broadcast the updated player list to everyone in the room
        await self.broadcast_player_update()
        print(f"Player '{player_name}' connected to room '{self.room_id}'. Host is '{self.host}'.")

    async def disconnect(self, player_name: str):
        """Removes a player and handles host migration."""
        if player_name in self.players:
            del self.players[player_name]
            del self.scores[player_name]
            
            # If the host disconnected, assign a new one
            if self.host == player_name:
                self.host = next(iter(self.players), None)
            
            # If the room is empty, stop any running game
            if not self.players and self.game_loop_task:
                 self.game_loop_task.cancel()

            await self.broadcast_player_update()
            print(f"Player '{player_name}' disconnected. New host is '{self.host}'.")

    async def broadcast(self, message: dict):
        """Sends a JSON message to all connected players in the room."""
        await asyncio.gather(
            *[player.send_json(message) for player in self.players.values()]
        )

    async def broadcast_player_update(self):
        """Sends the current list of players and scores to everyone."""
        # This matches the `player_update` message type from our protocol
        player_data = [
            {"name": name, "score": self.scores[name], "isHost": name == self.host}
            for name in self.players
        ]
        await self.broadcast({"type": "player_update", "payload": {"players": player_data}})

    # --- Game Logic ---

    async def handle_message(self, player_name: str, data: dict):
        """Handles incoming messages from a player."""
        message_type = data.get("type")
        payload = data.get("payload", {})

        # Only the host can start the game
        if message_type == "start_game" and player_name == self.host:
            await self.start_game()
        
        elif message_type == "new_guess":
            await self.process_guess(player_name, payload.get("guess"))

    async def start_game(self):
        """Starts the main game loop."""
        if self.game_state == "LOBBY":
            self.game_state = "IN_GAME"
            print(f"Room '{self.room_id}' is starting the game.")
            # Announce game start so the frontend can navigate
            await self.broadcast({"type": "game_started", "payload": {}})
            # Use asyncio.create_task to run the game loop in the background
            self.game_loop_task = asyncio.create_task(self.run_game_loop())

    async def run_game_loop(self):
        """Manages the sequence of rounds."""
        # For simplicity, let's run a fixed number of rounds
        for round_num in range(1, len(PROMPTS) + 1):
            if not self.players: # Stop if everyone leaves
                break
            await self.start_round(round_num)
            # Wait for the round to finish (timer ends or guess is correct)
            await asyncio.sleep(GAME_CONFIG["ROUND_DURATION_S"] + GAME_CONFIG["POST_ROUND_DELAY_S"])
        
        print(f"Game in room '{self.room_id}' has ended.")
        # TODO: Add a "game_over" message and logic
        self.game_state = "LOBBY" # Reset for a new game

    async def start_round(self, round_num: int):
        """Initializes a new round: gets prompt, generates image, and notifies players."""
        self.current_prompt = random.choice(PROMPTS)
        print(f"Room '{self.room_id}' Round {round_num}: Prompt is '{self.current_prompt}'")

        # Step 1: Generate the image from the AI Server
        image_b64 = await self.generate_ai_image(self.current_prompt)
        if not image_b64:
            print(f"Error: Failed to generate image for room '{self.room_id}'")
            # TODO: Handle image generation failure
            return
        self.current_image_b64 = image_b64
        
        # Step 2: Create the prompt hint
        prompt_hint = f"{len(self.current_prompt.split())} words"

        # Step 3: Broadcast the new turn state to all players
        await self.broadcast({
            "type": "new_turn",
            "payload": {
                "round": round_num,
                "totalRounds": len(PROMPTS),
                "timeLeft": GAME_CONFIG["ROUND_DURATION_S"],
                "imageBase64": self.current_image_b64,
                "promptHint": prompt_hint
            }
        })
        
        # Step 4: Start the round timer
        if self.round_timer_task:
            self.round_timer_task.cancel()
        self.round_timer_task = asyncio.create_task(self.round_timer())

    async def generate_ai_image(self, prompt: str) -> Optional[str]:
        """Connects to the AI server, sends a prompt, and returns the final base64 image."""
        try:
            async with websockets.connect(AI_SERVER_URI) as ai_websocket:
                await ai_websocket.send(prompt)
                last_image = None
                while True:
                    message = await ai_websocket.recv()
                    if message == "generation_complete":
                        return last_image
                    else:
                        # The message is a base64 string, just store the latest one
                        last_image = message
        except Exception as e:
            print(f"Could not connect to or communicate with AI server: {e}")
            return None

    async def round_timer(self):
        """Counts down the round duration and ends the round if time runs out."""
        await asyncio.sleep(GAME_CONFIG["ROUND_DURATION_S"])
        if self.game_state == "IN_GAME":
            print(f"Room '{self.room_id}' timer expired.")
            await self.end_round(winner=None, reason="Time is up!")

    async def process_guess(self, player_name: str, guess: str):
        """Processes a guess from a player."""
        if not guess: return

        # Broadcast the guess to everyone for chat history
        await self.broadcast({
            "type": "new_guess",
            "payload": {"player": player_name, "message": guess}
        })

        # Simple check: case-insensitive and ignores extra spaces.
        if guess.strip().lower() == self.current_prompt.lower():
            # Stop the timer since someone won
            if self.round_timer_task:
                self.round_timer_task.cancel()
            self.scores[player_name] += GAME_CONFIG["POINTS_FOR_CORRECT_GUESS"]
            await self.end_round(winner=player_name, reason=f"Guessed correctly!")

    async def end_round(self, winner: Optional[str], reason: str):
        """Ends the current round, calculates scores, and notifies players."""
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


class ConnectionManager:
    """Manages all active game rooms."""
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

# --- FastAPI App Setup ---
app = FastAPI()
manager = ConnectionManager()


# --- The Main WebSocket Endpoint for the Frontend ---
@app.websocket("/ws/game/{room_id}/{player_name}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, player_name: str):
    """Handles all WebSocket connections from the React frontend."""
    
    room = manager.get_or_create_room(room_id)

    # Prevent too many players or duplicate names
    if len(room.players) >= GAME_CONFIG["MAX_PLAYERS"] or player_name in room.players:
        await websocket.accept()
        await websocket.close(code=1008, reason="Room is full or name is taken.")
        return

    await room.connect(websocket, player_name)

    try:
        while True:
            # Wait for messages from this player
            data = await websocket.receive_json()
            # Pass the message to the room's handler
            await room.handle_message(player_name, data)
    except WebSocketDisconnect:
        # This block executes when a client disconnects
        print(f"WebSocket disconnected for player '{player_name}' in room '{room_id}'.")
    except Exception as e:
        print(f"An error occurred for player '{player_name}': {e}")
    finally:
        # Clean up the player from the room
        await room.disconnect(player_name)
        # Clean up the room if it's now empty
        manager.remove_room_if_empty(room_id)