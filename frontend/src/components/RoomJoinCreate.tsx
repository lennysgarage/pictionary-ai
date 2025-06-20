// src/components/RoomJoinCreate.tsx
import { Box, Button, Input, VStack, Text, HStack } from "@chakra-ui/react";
import { useState } from "react";
import { useGame } from "@/contexts/GameContext"; // Import our custom hook

export default function RoomJoinCreate() {
  const [roomId, setRoomId] = useState("");
  const [playerName, setPlayerName] = useState("");
  const { connect } = useGame(); // Get the connect function from context

  const handleConnect = (isCreating: boolean) => {
    const roomToJoin = isCreating ? Math.random().toString(36).substring(2, 8) : roomId;
    connect(roomToJoin, playerName);
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
          placeholder="Enter Your Name"
          size="lg"
          textAlign="center"
        />
        {/* <Divider my={2} /> */}
        <Button colorScheme="orange" size="lg" width="100%" onClick={() => handleConnect(true)} disabled={!playerName.trim()}>
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
          <Button colorScheme="blue" size="lg" onClick={() => handleConnect(false)} disabled={!playerName.trim() || !roomId.trim()}>
            Join
          </Button>
        </HStack>
      </VStack>
    </Box>
  );
}