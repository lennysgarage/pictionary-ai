// src/contexts/GameContext.tsx
import { createContext, useContext, useState, useRef, ReactNode } from 'react';
import { GameState, GameContextType } from '@/types';
import { useNavigate } from 'react-router-dom';

const GAME_SERVER_URL = process.env.GAME_SERVER_URL; // Your game server URL

// Initial state for the game
const initialState: GameState = {
  playerName: '',
  roomId: null,
  players: [],
  chatMessages: [],
  gameState: 'LOBBY',
  currentRound: 0,
  totalRounds: 0,
  timeLeft: 0,
  promptHint: '',
  currentImageB64: null,
  roundWinner: null,
  correctPrompt: null,
  roundEndReason: null,
  similarity: 0,
};

// Create the context with a default value
const GameContext = createContext<GameContextType | undefined>(undefined);

// The provider component that will wrap our app
export const GameProvider = ({ children }: { children: ReactNode }) => {
    const [gameState, setGameState] = useState<GameState>(initialState);
    const websocket = useRef<WebSocket | null>(null);
    const navigate = useNavigate();
  
    const handleServerMessage = (event: MessageEvent) => {
      const message = JSON.parse(event.data);
      console.log('Received message:', message);
  
      switch (message.type) {
        case 'player_update':
          setGameState(prev => ({ ...prev, players: message.payload.players }));
          break;
        case 'game_started':
          setGameState(prev => ({ ...prev, gameState: 'IN_GAME', chatMessages: [] }));
          navigate(`/game/${gameState.roomId}`);
          break;
        case 'new_turn':
          setGameState(prev => ({
            ...prev,
            gameState: 'IN_GAME',
            currentRound: message.payload.round,
            totalRounds: message.payload.totalRounds,
            timeLeft: message.payload.timeLeft,
            promptHint: message.payload.promptHint,
            // Set the image, which might be null initially
            currentImageB64: message.payload.imageBase64, 
            roundWinner: null,
            correctPrompt: null,
          }));
          break;
        
        // --- ADD THIS NEW CASE ---
        case 'image_update':
          setGameState(prev => ({
            ...prev,
            currentImageB64: message.payload.imageBase64,
          }));
          break;
  
        case 'new_guess':
          setGameState(prev => ({
            ...prev,
            chatMessages: [...prev.chatMessages, message.payload],
          }));
          break;
        case 'round_end':
          setGameState(prev => ({
            ...prev,
            gameState: 'POST_ROUND',
            correctPrompt: message.payload.correctPrompt,
            players: message.payload.scores,
          }));
          break;
        case 'guess_feedback':
            setGameState(prev => ({
                ...prev,
                similarity: message.payload.similarity,
            }));
            break;
        default:
          console.warn('Unknown message type:', message.type);
      }
    };
  

  const connect = (roomId: string, playerName: string) => {
    if (websocket.current) return; // Already connected

    const wsUrl = `${GAME_SERVER_URL}/${roomId}/${playerName}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log(`Connected to ${wsUrl}`);
      websocket.current = ws;
      setGameState({ ...initialState, roomId, playerName });
      navigate(`/lobby/${roomId}`);
    };

    ws.onmessage = handleServerMessage;

    ws.onclose = () => {
      console.log('Disconnected from WebSocket');
      websocket.current = null;
      setGameState(initialState);
      navigate('/');
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      ws.close();
    };
  };

  const disconnect = () => {
    websocket.current?.close();
  };

  const sendMessage = (type: string, payload: object = {}) => {
    if (websocket.current?.readyState === WebSocket.OPEN) {
      const message = JSON.stringify({ type, payload });
      websocket.current.send(message);
    }
  };

  const value = { gameState, connect, disconnect, sendMessage };

  return <GameContext.Provider value={value}>{children}</GameContext.Provider>;
};

// Custom hook to use the GameContext
export const useGame = () => {
  const context = useContext(GameContext);
  if (context === undefined) {
    throw new Error('useGame must be used within a GameProvider');
  }
  return context;
};