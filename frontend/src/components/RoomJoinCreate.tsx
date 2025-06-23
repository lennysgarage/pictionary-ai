import { Box, Button, Input, VStack, Text, HStack } from "@chakra-ui/react";
import { useState } from "react";
import { useGame } from "@/contexts/GameContext"; // Import our custom hook

export default function RoomJoinCreate() {
  const [roomId, setRoomId] = useState("");
  const [playerName, setPlayerName] = useState("");
  const { connect } = useGame(); // Get the connect function from context

  const handleConnect = async (isCreating: boolean) => {
      // If player name is empty, generate a random one.
      const nameToUse = playerName.trim() || `Guest-${Math.floor(1000 + Math.random() * 9000)}`;

        if (isCreating) {
            try {
                // Convert ws://... to http://... and remove the path to get the base URL
                const gameServerHttpUrl = import.meta.env.VITE_GAME_SERVER_URL.replace(/^ws/, 'http').split('/ws/game')[0];

                const response = await fetch(`${gameServerHttpUrl}/api/rooms`, {
                    method: 'POST',
                });

                if (!response.ok) {
                    throw new Error('Failed to create room on the server.');
                }
                const data = await response.json();
                connect(data.room_id, nameToUse);
            } catch (error) {
                console.error("Error creating room:", error);
                // You could add a user-facing error message here (e.g., using a toast)
            }
        } else {
            // Joining an existing room
            if (!roomId.trim()) return;
            connect(roomId, nameToUse);
        }
    };

    return (
        <Box p={8} borderWidth={1} borderRadius="lg" boxShadow="xl" bg="gray.700" minW="400px">
            <VStack gap={4}>
                <Text fontSize="2xl" fontWeight="bold" color="orange.300">
                    Promptanary
                </Text>
                <Input
                    value={playerName}
                    onChange={(e) => setPlayerName(e.target.value)}
                    placeholder="Enter Your Name (Optional)"
                    size="lg"
                    textAlign="center"
                />
                <Button colorScheme="orange" size="lg" width="100%" onClick={() => handleConnect(true)}>
                    Create a New Room
                </Button>
                <Text color="gray.400" fontWeight="bold">OR</Text>
                <HStack width="100%">
                    <Input
                        value={roomId}
                        onChange={(e) => setRoomId(e.target.value)}
                        placeholder="Enter Room ID"
                        size="lg"
                    />
                    <Button colorScheme="blue" size="lg" onClick={() => handleConnect(false)} disabled={!roomId.trim()}>
                        Join
                    </Button>
                </HStack>
            </VStack>
        </Box>
    );
}