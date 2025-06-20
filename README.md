# Promptanary!

A real-time image generation game where players guess prompts based on AI-generated images.

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- pip
- npm

### Backend Setup

1. **Install Python dependencies:**
```shell
pip intall -r requirements.txt
```

2. Two servers to start up, `ai_server.py` and `game_server.py`.
`ai_server.py` host the image generation and prompt similarity testing models.
`game_server.py` hosts the guessing game logic, controlling websocket connections to players aswell as retrieving images from the ai-server to broadcast to players.

### Frontend Setup
```shell
cd frontend/
```

1. **Install Node dependencies:**
```shell
npm i
```

2. **Run dev server:**
```shell
npm run dev
```

