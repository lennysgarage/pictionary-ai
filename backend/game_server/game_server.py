import asyncio
import websockets
import os
import random
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Optional, Any
import httpx
import string
import json

# --- Configuration & Prompts ---
AI_SERVER_URL = os.environ.get("AI_SERVER_URL", "ws://localhost:8000/ws/generate")
AI_SCORING_URL = os.environ.get("AI_SCORING_URL", "http://localhost:8000/score/similarity")

print(f"AI_SERVER_URL: {AI_SERVER_URL}")
print(f"AI_SCORING_URL: {AI_SCORING_URL}")

GAME_CONFIG = {
    "ROUND_DURATION_S": 30,
    "POST_ROUND_DELAY_S": 10,
    "MAX_PLAYERS": 12,
    "POINTS_FOR_CORRECT_GUESS": 1000
}

PROMPTS = [
    "A photorealistic portrait of a cat wearing a monocle", "A squirrel in the style of picasso",
    "Darth vader playing the drums", "An astronaut playing a trumpet on the moon",
    "Yoda playing the guitar", "An image of a crow sitting in a tree", "very long limo",
    "happy software engineer", "pug pikachu", "A boat down a river", "A blue coffee cup",
    "A vintage car", "A white dog sleeping on a couch", "Raindrops on a window",
    "A empty park bench", "stardew valley", "pope francis as a DJ in a nightclub",
    "landscape view from the Moon with the earth in the background", "cute toy owl made of suede",
    "industrial age pocket watch", "futuristic tree house", "oil painting of master chief",
    "the perfet bonsai tree", "albert einstein beside a chalkboard", "minecraft",
    "Dinosaur from jurassic park", "majestic royal tall ship on a calm sea",
    "Astronauts in a jungle, cold color palette", "A sloth riding a skateboard",
    "A robot chef making sushi", "A paper airplane", "A car driving on a winding road",
    "A professor giving a lecture", "A rocket launching into space", "A dog catching a frisbee",
    "A robot serving coffee", "A playful otter juggling", "A cat napping in a sunbeam",
    "A friendly ghost sipping tea", "A single red rose in glass vase", "A stack of books",
]

# --- GameRoom Class (with modifications) ---

class GameRoom:
    """Manages the state and logic for a single game room."""

    def __init__(self, room_id: str):
        self.room_id: str = room_id
        self.host: Optional[str] = None
        self.players: Dict[str, WebSocket] = {}
        self.scores: Dict[str, int] = {}
        self.game_state: str = "LOBBY"
        self.current_prompt: str = ""
        self.current_image_b64: str = ""
        self.round_timer_task: Optional[asyncio.Task] = None
        self.game_loop_task: Optional[asyncio.Task] = None
        self.image_stream_task: Optional[asyncio.Task] = None
        self.round_start_time: float = 0.0
        self.round_best_scores: Dict[str, int] = {}
        self.round_best_similarities: Dict[str, float] = {}
        print(f"Room {room_id} created.")

    def get_full_game_state(self) -> Dict[str, Any]:
        """Helper method to assemble the complete game state for a new player."""
        player_data = [
            {
                "name": name,
                "score": self.scores[name],
                "isHost": name == self.host,
                "bestSimilarity": self.round_best_similarities.get(name, 0.0)
            }
            for name in self.players
        ]
        return {
            "roomId": self.room_id,
            "players": player_data,
            "gameState": self.game_state,
            "currentRound": 0, # Or actual if mid-game
            "totalRounds": 10,
            "timeLeft": 0, # Or actual
            "promptHint": f"{len(self.current_prompt.split())} words" if self.current_prompt else "",
            "currentImageB64": self.current_image_b64,
            "correctPrompt": self.current_prompt if self.game_state == 'POST_ROUND' else None,
        }
    
    # MODIFIED: Connect method sends full state back to joining player
    async def connect(self, websocket: WebSocket, player_name: str):
        self.players[player_name] = websocket
        self.scores[player_name] = 0
        if self.host is None:
            self.host = player_name
        
        # Send a success message with the full state to the connecting player
        await websocket.send_json({
            "type": "join_success",
            "payload": self.get_full_game_state()
        })

        # Broadcast an update to everyone else
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
        # Create a list of players to iterate over to avoid issues if the dict changes during iteration
        players_to_send = list(self.players.values())
        await asyncio.gather(
            *[player.send_json(message) for player in players_to_send],
            return_exceptions=True # Set to True to see errors if a send fails
        )

    async def broadcast_player_update(self):
        player_data = [
            {
                "name": name,
                "score": self.scores[name],
                "isHost": name == self.host,
                "bestSimilarity": self.round_best_similarities.get(name, 0.0)
            }
            for name in self.players
        ]
        await self.broadcast({"type": "player_update", "payload": {"players": player_data}})

    async def handle_message(self, player_name: str, data: dict):
        message_type = data.get("type")
        payload = data.get("payload", {})
        print(f"Room '{self.room_id}' received message from '{player_name}': {message_type}")

        if message_type == "start_game" and player_name == self.host:
            await self.start_game()
        elif message_type == "new_guess":
            await self.process_guess(player_name, payload.get("guess"))
    
    # (Game logic methods like start_game, run_game_loop, start_round, etc. remain the same)
    # --- Game Logic (No changes from here down, just including for completeness) ---

    async def start_game(self):
        if self.game_state == "LOBBY":
            self.game_state = "IN_GAME"
            print(f"Room '{self.room_id}' is starting the game.")
            await self.broadcast({"type": "game_starting", "payload": {"roomId": self.room_id}})
            self.game_loop_task = asyncio.create_task(self.run_game_loop())

    async def run_game_loop(self):
        for round_num in range(1, 11):
            if not self.players:
                break
            await self.start_round(round_num)
            await asyncio.sleep(GAME_CONFIG["ROUND_DURATION_S"] + GAME_CONFIG["POST_ROUND_DELAY_S"])
        print(f"Game in room '{self.room_id}' has ended.")
        self.game_state = "LOBBY"

    async def start_round(self, round_num: int):
        self.game_state = "IN_GAME"
        self.current_prompt = random.choice(PROMPTS)
        self.round_best_scores.clear()
        self.round_best_similarities.clear()
        self.round_start_time = time.time()
        print(f"Room '{self.room_id}' Round {round_num}: Prompt is '{self.current_prompt}'")
        await self.broadcast({
            "type": "new_turn",
            "payload": {
                "round": round_num, "totalRounds": 10,
                "timeLeft": GAME_CONFIG["ROUND_DURATION_S"],
                "imageBase64": None,
                "promptHint": f"{len(self.current_prompt.split())} words"
            }
        })
        await self.broadcast_player_update()
        if self.round_timer_task: self.round_timer_task.cancel()
        if self.image_stream_task: self.image_stream_task.cancel()
        self.round_timer_task = asyncio.create_task(self.round_timer())
        self.image_stream_task = asyncio.create_task(self.run_image_generation_and_broadcast())

    async def run_image_generation_and_broadcast(self):
        try:
            async with websockets.connect(AI_SERVER_URL) as ai_websocket:
                await ai_websocket.send(self.current_prompt)
                while True:
                    message = await ai_websocket.recv()
                    if message == "generation_complete":
                        print(f"Room '{self.room_id}': Generation complete.")
                        break
                    self.current_image_b64 = message.decode('utf-8') if isinstance(message, bytes) else message
                    full_data_url = f"data:image/png;base64,{self.current_image_b64}"
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
            await self.end_round()
            
    async def process_guess(self, player_name: str, guess: str):
        if not guess or self.game_state != "IN_GAME": return
        similarity = 0.0
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(AI_SCORING_URL, json={"prompt": self.current_prompt, "guess": guess}, timeout=10.0)
                response.raise_for_status()
                similarity = response.json().get("score", 0.0)
        except httpx.RequestError as e:
            print(f"Error calling AI scoring server: {e}")
            similarity = -1
        
        player_websocket = self.players.get(player_name)
        if player_websocket:
            await player_websocket.send_json({"type": "guess_feedback", "payload": {"similarity": round(similarity, 2)}})
        
        if similarity < 0: return

        current_best_similarity = self.round_best_similarities.get(player_name, 0.0)
        if similarity > current_best_similarity:
            self.round_best_similarities[player_name] = similarity
            await self.broadcast_player_update()

        base_points = int(GAME_CONFIG["POINTS_FOR_CORRECT_GUESS"] * (similarity / 100))
        time_elapsed = time.time() - self.round_start_time
        round_progress = min(1.0, time_elapsed / GAME_CONFIG["ROUND_DURATION_S"])
        time_modifier = 1.0
        if round_progress > 0.8:
            time_modifier = 1.5 - round_progress
        potential_new_score = int(base_points * time_modifier)
        current_best_score = self.round_best_scores.get(player_name, 0)

        if potential_new_score > current_best_score:
            points_to_add = potential_new_score - current_best_score
            self.scores[player_name] += points_to_add
            self.round_best_scores[player_name] = potential_new_score
            print(f"IMPROVEMENT for '{player_name}': New round score is {potential_new_score}. Added {points_to_add} to total.")
            await self.broadcast_player_update()

    async def end_round(self):
        if self.image_stream_task: self.image_stream_task.cancel()
        self.game_state = "POST_ROUND"
        print(f"Room '{self.room_id}' round ended.")
        await self.broadcast({
            "type": "round_end",
            "payload": {
                "correctPrompt": self.current_prompt,
                "scores": [{"name": name, "score": self.scores[name]} for name in self.players],
                "roundBestSimilarities": self.round_best_similarities
            }
        })

# --- ConnectionManager and FastAPI App ---
class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, GameRoom] = {}
        # NEW: Track WebSocket to player mapping to find them on disconnect
        self.active_connections: Dict[WebSocket, tuple[str, str]] = {}

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

# (origins list and CORSMiddleware remain the same)
origins = [
    "http://localhost:5173", "http://127.0.0.1:5173", "https://pictionary-ai.pages.dev"
]
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

@app.post("/api/rooms")
async def create_room_endpoint():
    while True:
        room_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        if room_id not in manager.rooms:
            break
    manager.get_or_create_room(room_id)
    print(f"New room created via API endpoint: {room_id}")
    return {"room_id": room_id}

@app.websocket("/ws/game")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    room = None
    player_name = None
    room_id = None
    try:
        # The first message MUST be a 'join_room' message
        initial_data = await websocket.receive_json()
        message_type = initial_data.get("type")
        payload = initial_data.get("payload", {})

        if message_type == "join_room":
            room_id = payload.get("room_id")
            player_name = payload.get("player_name")

            if not room_id or not player_name:
                await websocket.close(code=1008, reason="Missing room_id or player_name")
                return

            room = manager.get_or_create_room(room_id)

            if len(room.players) >= GAME_CONFIG["MAX_PLAYERS"]:
                await websocket.send_json({"type": "error", "message": "room_full"})
                await websocket.close()
                return

            if player_name in room.players:
                await websocket.send_json({"type": "error", "message": "name_taken"})
                await websocket.close()
                return

            # Store connection info for disconnect handling
            manager.active_connections[websocket] = (room_id, player_name)
            await room.connect(websocket, player_name)

            # Now, listen for subsequent messages in a loop
            while True:
                data = await websocket.receive_json()
                await room.handle_message(player_name, data)
        else:
            await websocket.close(code=1008, reason="First message was not join_room")
            return

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for player '{player_name}' in room '{room_id}'.")
    except Exception as e:
        print(f"An unexpected error occurred for {player_name} in {room_id}: {e}")
    finally:
        # Clean up on disconnect
        if websocket in manager.active_connections:
            room_id, player_name = manager.active_connections.pop(websocket)
            if room_id and player_name and room_id in manager.rooms:
                room = manager.rooms[room_id]
                await room.disconnect(player_name)
                manager.remove_room_if_empty(room_id)
