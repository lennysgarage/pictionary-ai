import asyncio
import websockets
import os
import random
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, Optional
import httpx


# --- Configuration & Prompts (No changes here) ---
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
    "A photorealistic portrait of a cat wearing a monocle",
    "A squirrel in the style of picasso",
    "Darth vader playing the drums",
    "An astronaut playing a trumpet on the moon",
    "Yoda playing the guitar",
    "An image of a crow sitting in a tree",
    "very long limo",
    "happy software engineer",
    "pug pikachu",
    "A boat down a river",
    "A blue coffee cup",
    "A vintage car",
    "A white dog sleeping on a couch",
    "Raindrops on a window",
    "A empty park bench",
    "stardew valley",
    "pope francis as a DJ in a nightclub",
    "landscape view from the Moon with the earth in the background",
    "cute toy owl made of suede",
    "industrial age pocket watch",
    "futuristic tree house",
    "oil painting of master chief"
    "the perfet bonsai tree",
    "albert einstein beside a chalkboard",
    "minecraft",
    "Mad max and dinosaur from jurassic park",
    "majestic royal tall ship on a calm sea",
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
        self.current_image_b64: str = ""
        self.round_timer_task: Optional[asyncio.Task] = None
        self.game_loop_task: Optional[asyncio.Task] = None
        # NEW: Add a task for the image generation stream
        self.image_stream_task: Optional[asyncio.Task] = None
        self.round_start_time: float = 0.0
        self.round_best_scores: Dict[str, int] = {}
        # NEW: Track highest similarity for each player in current round
        self.round_best_similarities: Dict[str, float] = {}
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
        for round_num in range(1, 11): # at most 10 rounds
            if not self.players:
                break
            await self.start_round(round_num)
            await asyncio.sleep(GAME_CONFIG["ROUND_DURATION_S"] + GAME_CONFIG["POST_ROUND_DELAY_S"])
        
        print(f"Game in room '{self.room_id}' has ended.")
        self.game_state = "LOBBY"

    async def start_round(self, round_num: int):
        """Initializes a round, sends initial data, THEN starts the image stream."""
        self.game_state = "IN_GAME"
        self.current_prompt = random.choice(PROMPTS)
        self.round_best_scores.clear()
        self.round_best_similarities.clear()
        self.round_start_time = time.time()
        print(f"Room '{self.room_id}' Round {round_num}: Prompt is '{self.current_prompt}'")

        # Step 1: Broadcast the new turn signal with a NULL image initially.
        # This tells the UI to get ready for the stream.
        await self.broadcast({
            "type": "new_turn",
            "payload": {
                "round": round_num,
                "totalRounds": 10,
                "timeLeft": GAME_CONFIG["ROUND_DURATION_S"],
                "imageBase64": None, # Initially null
                "promptHint": f"{len(self.current_prompt.split())} words"
            }
        })
        
        # Step 2: Broadcast updated player data with reset similarities
        await self.broadcast_player_update()
        
        # Step 3: Start the background tasks for the timer AND the image stream
        if self.round_timer_task: self.round_timer_task.cancel()
        if self.image_stream_task: self.image_stream_task.cancel()
        
        self.round_timer_task = asyncio.create_task(self.round_timer())
        self.image_stream_task = asyncio.create_task(self.run_image_generation_and_broadcast())

    async def run_image_generation_and_broadcast(self):
        """Connects to AI server and broadcasts each image chunk as it arrives."""
        try:
            async with websockets.connect(AI_SERVER_URL) as ai_websocket:
                await ai_websocket.send(self.current_prompt)
                
                while True:
                    message = await ai_websocket.recv()
                    
                    if message == "generation_complete":
                        print(f"Room '{self.room_id}': Generation complete.")
                        break # End this task
                    
                    # We received an image chunk. Broadcast it immediately.
                    self.current_image_b64 = message.decode('utf-8') if isinstance(message, bytes) else message # Keep track of the latest image
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
            await self.end_round()

    async def process_guess(self, player_name: str, guess: str):
        """
        Processes multiple guesses per player, sending private feedback for each
        and only updating their score if they achieve a new high score for the round.
        """
        # --- 1. Initial Checks ---
        if not guess or self.game_state != "IN_GAME":
            return

        # --- 2. Get Similarity Score from AI Server ---
        similarity = 0.0
        try:
            async with httpx.AsyncClient() as client:
                # This part is unchanged - we still call the AI server
                response = await client.post(
                    AI_SCORING_URL,
                    json={"prompt": self.current_prompt, "guess": guess},
                    timeout=10.0
                )
                response.raise_for_status()
                similarity = response.json().get("score", 0.0)
        except httpx.RequestError as e:
            print(f"Error calling AI scoring server: {e}")
            # Still send feedback to the user, even if there was an error
            similarity = -1 # Use a negative number to indicate an error state

        # --- 3. Send PRIVATE Feedback to the Guesser ---
        # Get the specific player's websocket connection
        player_websocket = self.players.get(player_name)
        if player_websocket:
            await player_websocket.send_json({
                "type": "guess_feedback",
                "payload": {
                    "similarity": round(similarity, 2)
                }
            })
        
        # If there was a scoring error, stop here
        if similarity < 0:
            return

        # --- 4. Update Best Similarity for the Round ---
        current_best_similarity = self.round_best_similarities.get(player_name, 0.0)
        if similarity > current_best_similarity:
            self.round_best_similarities[player_name] = similarity
            # Broadcast updated player information to show new best similarity
            await self.broadcast_player_update()

        # --- 5. Calculate Potential Score (from Similarity + Time) ---
        base_points = int(GAME_CONFIG["POINTS_FOR_CORRECT_GUESS"] * (similarity / 100))

        # Time decay
        time_elapsed = time.time() - self.round_start_time
        round_progress = min(1.0, time_elapsed / GAME_CONFIG["ROUND_DURATION_S"])
        time_modifier = 1.0 # No penalty in the first half

        # Apply penalty only in the second half of the round
        if round_progress > 0.8:
            time_modifier = 1.5 - round_progress
            
        potential_new_score = int(base_points * time_modifier)
        # --- 6. Update Total Score Only If It's a New Best ---
        current_best_score = self.round_best_scores.get(player_name, 0)

        if potential_new_score > current_best_score:
            # Calculate the *difference* to add to the player's permanent score
            points_to_add = potential_new_score - current_best_score
            
            # Update the permanent total score
            self.scores[player_name] += points_to_add
            
            # Update the best score for this round
            self.round_best_scores[player_name] = potential_new_score
            
            print(f"IMPROVEMENT for '{player_name}': New round score is {potential_new_score}. Added {points_to_add} to total.")

            # Broadcast the updated scoreboard to ALL players
            await self.broadcast_player_update()

    async def end_round(self):
        # Stop all background tasks for this round
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