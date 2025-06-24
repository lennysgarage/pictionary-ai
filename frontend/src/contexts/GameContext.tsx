import { createContext, useContext, useState, useRef, ReactNode, useCallback, useEffect } from 'react';
import { GameState, GameContextType } from '@/types';
import { useNavigate } from 'react-router-dom';

const GAME_SERVER_URL = import.meta.env.VITE_GAME_SERVER_URL; // Your game server URL

// Initial state for the game
const initialState: GameState = {
  playerName: '',
  roomId: null,
  players: [],
  chatMessages: [],
  gameState: 'LOBBY',
  currentRound: 0,
  totalRounds: 10,
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
    const webSocketRef = useRef<WebSocket | null>(null);
    const navigate = useNavigate();

    // Central message handler
    const handleServerMessage = useCallback((event: MessageEvent) => {
        const data = JSON.parse(event.data);
        console.log("Received message:", data);

        switch (data.type) {
            case 'join_success':
            case 'game_state_update':
                // CRITICAL FIX: Merge the server's state with the existing state.
                // This preserves the client's `playerName` while updating everything else.
                setGameState(prev => ({ ...prev, ...data.payload }));
                
                if (data.type === 'join_success' && data.payload.roomId) {
                    navigate(`/lobby/${data.payload.roomId}`);
                }
                break;
            
            case 'player_update':
                setGameState(prev => ({ ...prev, players: data.payload.players }));
                break;
            
            case 'game_starting':
                setGameState(prev => ({ ...prev, gameState: 'IN_GAME', chatMessages: [], ...data.payload }));
                break;
            
            case 'new_turn':
                setGameState(prev => ({
                    ...prev,
                    gameState: 'IN_GAME',
                    currentRound: data.payload.round,
                    totalRounds: data.payload.totalRounds,
                    timeLeft: data.payload.timeLeft,
                    currentImageB64: data.payload.imageBase64,
                    promptHint: data.payload.promptHint,
                    roundWinner: null,
                    correctPrompt: null,
                    similarity: 0,
                }));
                break;

            case 'image_update':
                 setGameState(prev => ({
                    ...prev,
                    currentImageB64: data.payload.imageBase64,
                 }));
                 break;

            case 'round_end':
                setGameState(prev => ({
                    ...prev,
                    gameState: 'POST_ROUND',
                    correctPrompt: data.payload.correctPrompt,
                }));
                break;

            case 'guess_feedback':
                setGameState(prev => ({
                    ...prev,
                    similarity: data.payload.similarity,
                }));
                break;

            case 'error':
                console.error("Server error:", data.message);
                alert(`Error from server: ${data.message}`);
                disconnect();
                break;

            default:
                console.warn("Unhandled message type:", data.type);
        }
    }, [navigate]);

    const sendMessage = useCallback((type: string, payload?: object) => {
        if (webSocketRef.current?.readyState === WebSocket.OPEN) {
            const message = JSON.stringify({ type, payload });
            webSocketRef.current.send(message);
        } else {
            console.error('WebSocket is not connected.');
        }
    }, []);

    const disconnect = useCallback(() => {
        if (webSocketRef.current) {
            webSocketRef.current.close();
            webSocketRef.current = null;
        }
        setGameState(initialState);
        navigate('/');
    }, [navigate]);
    
    const connect = useCallback((roomId: string, playerName: string) => {
        if (webSocketRef.current && webSocketRef.current.readyState !== WebSocket.CLOSED) {
            console.log("WebSocket is already connecting or open.");
            return;
        }

        setGameState({ ...initialState, playerName });

        const ws = new WebSocket(GAME_SERVER_URL);
        webSocketRef.current = ws;

        ws.onopen = () => {
            console.log('WebSocket connection established. Sending join_room message.');
            sendMessage('join_room', { room_id: roomId, player_name: playerName });
        };

        ws.onmessage = handleServerMessage;

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            webSocketRef.current = null;
            disconnect();
        };

        ws.onclose = (event) => {
            console.log('WebSocket connection closed.', event.reason);
            disconnect();
        };
    }, [sendMessage, handleServerMessage, disconnect]);

    useEffect(() => {
        if (gameState.gameState === 'IN_GAME' && gameState.roomId) {
            if (!window.location.pathname.startsWith(`/game/${gameState.roomId}`)) {
                 navigate(`/game/${gameState.roomId}`);
            }
        }
    }, [gameState.gameState, gameState.roomId, navigate]);

    const value = { gameState, connect, disconnect, sendMessage };

    return <GameContext.Provider value={value}>{children}</GameContext.Provider>;
};

export const useGame = () => {
    const context = useContext(GameContext);
    if (context === undefined) {
        throw new Error('useGame must be used within a GameProvider');
    }
    return context;
};