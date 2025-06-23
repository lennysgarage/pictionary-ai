// src/components/Lobby.tsx
import { Box, Button, VStack, Text, Grid, Icon, Heading, HStack, Clipboard } from "@chakra-ui/react";
import { Toaster, toaster } from "@/components/ui/toaster";
import { FaUserCircle, FaCrown } from "react-icons/fa";
import { useGame } from "@/contexts/GameContext";
import { useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom"; 
import Header from "./Header";

export default function Lobby() {
    const { gameState, connect, sendMessage } = useGame();
    const { players, playerName } = gameState;
    const { roomId: roomIdFromParams } = useParams<{ roomId: string }>(); // Get roomId from URL
    const navigate = useNavigate();

    const hasToastBeenShown = useRef(false);

    const isHost = players.find(p => p.name === playerName)?.isHost || false;

    // This effect handles joining a lobby directly via a shared link
    useEffect(() => {
        // If we have a room ID from the URL but are not yet connected, connect now.
        if (roomIdFromParams && !gameState.roomId) {
            const randomPlayerName = `Guest-${Math.floor(1000 + Math.random() * 9000)}`;
            console.log(`Attempting to auto-join room '${roomIdFromParams}' as '${randomPlayerName}'`);
            connect(roomIdFromParams, randomPlayerName);
        }
    }, [roomIdFromParams, gameState.roomId, connect]);

    // This effect is for showing the "Joined" toast. It now triggers when a player name is confirmed.
    useEffect(() => {
        if (gameState.roomId && gameState.playerName && !hasToastBeenShown.current) {
            toaster.create({
                title: 'Joined Lobby!',
                description: `Room ID: ${gameState.roomId}. Share the page URL to invite friends!`,
                duration: 5000,
                closable: true,
            });
            hasToastBeenShown.current = true;
        }
    }, [gameState.roomId, gameState.playerName]);

    const handleStartGame = () => {
        sendMessage("start_game");
    };

    // If there's no room ID in the URL, we can't be in a lobby. Go home.
    if (!roomIdFromParams) {
        useEffect(() => {
            navigate('/');
        }, [navigate]);
        return null;
    }

    // While connecting, show a loading state until we have a player name.
    if (!gameState.playerName) {
        return (
            <Box>
                <Header />
                <Text fontSize="xl" color="gray.300" mt={10}>Joining room...</Text>
            </Box>
        );
    }

    return (
        <Box>
            <Header />
            <Box textAlign="center" p={8} borderWidth={1} borderRadius="lg" boxShadow="xl" bg="gray.700" minW="600px">
                <Toaster />
                <VStack gap={4}>
                    <Heading color="orange.300">Lobby</Heading>
                    <HStack>
                        <Text fontSize="lg">Room ID: <Text as="span" fontWeight="bold" color="yellow.400">{gameState.roomId}</Text></Text>
                        <Clipboard.Root value={gameState.roomId ? gameState.roomId : ""}>
                            <Clipboard.Trigger asChild>
                                <Button size="xs" colorScheme="gray" variant="subtle" _hover={{ bg: "gray.600" }}>
                                    <Clipboard.Indicator />
                                </Button>
                            </Clipboard.Trigger>
                        </Clipboard.Root>
                    </HStack>
                    <Text fontSize="md" color="gray.400">Share the page URL to invite others!</Text>
                    <Grid templateColumns="repeat(4, 1fr)" gap={6} w="100%" pt={4}>
                        {players.map((player) => (
                            <VStack key={player.name} p={4} bg="gray.600" borderRadius="md" boxShadow="md" position="relative">
                                {player.isHost && <Icon as={FaCrown} color="yellow.400" position="absolute" top={2} right={2} />}
                                <Icon as={FaUserCircle} w={12} h={12} color="orange.200" />
                                <Text fontWeight={player.name === playerName ? 'bold' : 'normal'}>{player.name}</Text>
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