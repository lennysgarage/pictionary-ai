// src/components/Lobby.tsx
import { Box, Button, VStack, Text, Grid, Icon, Heading, HStack, Clipboard } from "@chakra-ui/react";
import { Toaster, toaster } from "@/components/ui/toaster";
import { FaUserCircle, FaCrown } from "react-icons/fa";
import { useGame } from "@/contexts/GameContext";
import { useEffect } from "react";
import Header from "./Header";

export default function Lobby() {
    const { gameState, sendMessage } = useGame();
    const { roomId, players, playerName } = gameState;

    const isHost = players.find(p => p.name === playerName)?.isHost || false;

    useEffect(() => {
        if (roomId) {
            toaster.create({
                title: 'Joined Lobby!',
                description: `Room ID: ${roomId}. Share it with your friends!`,
                duration: 5000,
                closable: true,
            });
        }
    }, [roomId]);

    const handleStartGame = () => {
        sendMessage("start_game");
    };

    return (
        <Box>
            <Header />
            <Box textAlign="center" p={8} borderWidth={1} borderRadius="lg" boxShadow="xl" bg="gray.700" minW="600px">
                <Toaster />
                <VStack gap={6}>
                    <Heading color="orange.300">Lobby</Heading>
                    <HStack>
                        <Text fontSize="lg">Room ID: <Text as="span" fontWeight="bold" color="yellow.400">{roomId}</Text></Text>
                        <Clipboard.Root value={roomId ? roomId : undefined}>
                            <Clipboard.Trigger>
                                <Button size="xs" colorScheme="gray" variant="subtle" _hover={{ bg: "gray.600" }}>
                                    <Clipboard.Indicator />
                                </Button>
                            </Clipboard.Trigger>
                        </Clipboard.Root>
                    </HStack>
                    <Grid templateColumns="repeat(4, 1fr)" gap={6} w="100%" pt={4}>
                        {players.map((player) => (
                            <VStack key={player.name} p={4} bg="gray.600" borderRadius="md" boxShadow="md" position="relative">
                                {player.isHost && <Icon as={FaCrown} color="yellow.400" position="absolute" top={2} right={2} />}
                                <Icon as={FaUserCircle} w={12} h={12} color="orange.200" />
                                <Text fontWeight={player.name === playerName ? 'bold' : 'normal'}>{player.name}</Text>
                                <Text fontSize="sm" color="gray.300">{player.score}</Text>
                            </VStack>
                        ))}
                    </Grid>
                    {isHost ? (
                        <Button colorScheme="green" size="lg" width="50%" onClick={handleStartGame} disabled={players.length < 1}>
                            Start Game ({players.length}/{12})
                        </Button>
                    ) : (
                        <Text color="gray.300" mt={8}>Waiting for the host to start the game...</Text>
                    )}
                </VStack>
            </Box>
        </Box>
    );
}