// src/components/RoomJoinCreate.tsx
import { Box, Button, Input, VStack, HStack, Text } from "@chakra-ui/react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function RoomJoinCreate() {
  const [roomId, setRoomId] = useState("");
  const navigate = useNavigate();

  const handleCreateRoom = () => {
    // Generate a simple 6-character random room ID
    const newRoomId = Math.random().toString(36).substring(2, 8);
    navigate(`/lobby/${newRoomId}`);
  };

  const handleJoinRoom = () => {
    if (roomId.trim()) {
      navigate(`/lobby/${roomId}`);
    }
  };

  return (
    <Box
      p={8}
      borderWidth={1}
      borderRadius="lg"
      boxShadow="xl"
      bg="gray.700"
      minW="400px"
    >
      <VStack gap={6}>
        <Text fontSize="2xl" fontWeight="bold" color="orange.300" >
          Get Started
        </Text>
        
        <Button
          colorScheme="orange"
          size="lg"
          width="100%"
          onClick={handleCreateRoom}
        >
          Create a New Room
        </Button>

        <HStack width="100%" align="center" justify="center">
          {/* <Divider /> */}
          <Text px={2}  whiteSpace="nowrap" color="gray.400">OR</Text>
          {/* <Divider /> */}
        </HStack>

        <VStack width="100%" gap={3}>
          <Input
            value={roomId}
            onChange={(e) => setRoomId(e.target.value)}
            placeholder="Enter Room ID to Join"
            size="lg"
            textAlign="center"
          />
          <Button
            colorScheme="blue"
            size="lg"
            width="100%"
            onClick={handleJoinRoom}
            disabled={!roomId.trim()}
          >
            Join Room
          </Button>
        </VStack>
      </VStack>
    </Box>
  );
}