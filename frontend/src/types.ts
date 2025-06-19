export interface Player {
    name: string;
    score: number;
    isHost: boolean;
  }
  
  export interface ChatMessage {
    player: string;
    message: string;
  }
  
  // This interface represents the entire state of our game
  export interface GameState {
    playerName: string;
    roomId: string | null;
    players: Player[];
    chatMessages: ChatMessage[];
    gameState: 'LOBBY' | 'IN_GAME' | 'POST_ROUND';
    currentRound: number;
    totalRounds: number;
    timeLeft: number;
    promptHint: string;
    currentImageB64: string | null;
    roundWinner: string | null;
    correctPrompt: string | null;
    roundEndReason: string | null;
  }
  
  // This defines the structure of the context we will provide
  export interface GameContextType {
    gameState: GameState;
    connect: (roomId: string, playerName: string) => void;
    disconnect: () => void;
    sendMessage: (type: string, payload?: object) => void;
  }