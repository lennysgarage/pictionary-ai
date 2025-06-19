// src/components/Lobby.tsx
import { Box, Button, VStack, Text, Grid, Icon, Heading } from "@chakra-ui/react";
import { Toaster, toaster } from "@/components/ui/toaster"
import { useParams, useNavigate } from "react-router-dom";
// import { useWebSocket } from "../hooks/useWebSocket"; // We'll comment this out for now
import { useState, useEffect } from "react";
import { FaUserCircle } from "react-icons/fa";

// Mock player data
const MOCK_PLAYERS = ["You", "Arturo", "Beatrice", "Carlos"];

export default function Lobby() {
  const { roomId } = useParams();
  const navigate = useNavigate();
  const [players, setPlayers] = useState<string[]>([]);

  // We are not using the real WebSocket for now.
  // useWebSocket(`ws://localhost:8000/ws/lobby/${roomId}`, (msg) => {
  //   if (msg.type === "players") setPlayers(msg.players);
  //   if (msg.type === "start_game") navigate(`/game/${roomId}`);
  // });

  // MOCK: Simulate players joining the lobby
  useEffect(() => {
    setPlayers([MOCK_PLAYERS[0]]); // Start with the current player
    
    // Simulate other players joining one by one
    for (let i = 1; i < MOCK_PLAYERS.length; i++) {
      setTimeout(() => {
        setPlayers(prev => [...prev, MOCK_PLAYERS[i]]);
      }, 1000 * i);
    }

    toaster.create({
      title: 'Joined Lobby!',
      description: `Room ID: ${roomId}. Share it with your friends!`,
      duration: 5000,
    });
  }, []);

  const handleStartGame = () => {
    // In a real app, you would send a "start_game" message via WebSocket
    // The server would then broadcast a message that triggers the navigation
    // For now, we navigate directly.
    console.log("Starting game...");
    navigate(`/game/${roomId}`);
  };

  return (
    <Box textAlign="center" p={8} borderWidth={1} borderRadius="lg" boxShadow="xl" bg="gray.700" minW="600px">
    <Toaster />
      <VStack gap={6}>
        <Heading color="orange.300">Lobby</Heading>
        <Text fontSize="lg">Room ID: <Text as="span" fontWeight="bold" color="yellow.400">{roomId}</Text></Text>
        <Text color="gray.300">Waiting for players to join...</Text>

        <Grid templateColumns="repeat(4, 1fr)" gap={6} w="100%" pt={4}>
          {players.map((player, index) => (
            <VStack key={index} p={4} bg="gray.600" borderRadius="md" boxShadow="md">
              <Icon as={FaUserCircle} w={12} h={12} color="orange.200" />
              <Text fontWeight="bold">{player}</Text>
            </VStack>
          ))}
        </Grid>

        <VStack gap={4} pt={6} w="full">
          {/* Typically, only the host would see this button */}
          <Button
            colorScheme="green"
            size="lg"
            width="50%"
            onClick={handleStartGame}
            disabled={players.length < 2} // Can't start a game alone
          >
            Start Game!
          </Button>
          <Button colorScheme="red" variant="outline" mt={2} onClick={() => navigate("/")}>
            Leave Lobby
          </Button>
        </VStack>
      </VStack>
    </Box>
  );
}