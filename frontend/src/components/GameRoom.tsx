// src/components/GameRoom.tsx
import { Box, Button, VStack, Text, Input, HStack, Grid, GridItem, Heading, Progress, Flex, Spacer, Image, Dialog } from "@chakra-ui/react";
import { useState, useEffect } from "react";
import { useGame } from "@/contexts/GameContext";

const PLACEHOLDER_IMAGE = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";

export default function GameRoom() {
  const { gameState, sendMessage, disconnect } = useGame();
  const { players, chatMessages, currentRound, totalRounds, timeLeft, promptHint, currentImageB64, roundWinner, correctPrompt, roundEndReason, gameState: roomState } = gameState;

  const [guess, setGuess] = useState("");
  const [timer, setTimer] = useState(timeLeft);

  // Client-side timer for smoother UI
  useEffect(() => {
    setTimer(timeLeft);
    const interval = setInterval(() => {
      setTimer(prev => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [timeLeft]);

  const handleGuessSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!guess.trim()) return;
    sendMessage("new_guess", { guess });
    setGuess("");
  };

  const sortedPlayers = [...players].sort((a, b) => b.score - a.score);

  return (
    <>
      <Grid templateAreas={`"header header header" "players image chat" "players guess chat"`} gridTemplateRows={'auto 1fr auto'} gridTemplateColumns={'250px 1fr 300px'} h="calc(100vh - 160px)" w="100%" gap='4'>
        {/* HEADER AREA */}
        <GridItem area={'header'} bg="gray.700" p={2} borderRadius="md">
          <Flex align="center">
            <Box w="120px"><Text>Round {currentRound}/{totalRounds}</Text></Box>
            <Spacer />
            <Heading size="lg" color="yellow.400">{promptHint}</Heading>
            <Spacer />
            <Box w="120px" textAlign="right"><Text fontSize="2xl" fontWeight="bold">{timer}s</Text></Box>
          </Flex>
          {/* <Progress value={(timer / timeLeft) * 100} colorScheme="orange" size="sm" mt={1} /> */}
        </GridItem>

        {/* PLAYER LIST / SCOREBOARD */}
        <GridItem area={'players'} bg="gray.800" p={4} borderRadius="md"><VStack align="stretch" gap={3}><Heading size="md" mb={2}>Scoreboard</Heading>{sortedPlayers.map((p, i) => (<Flex key={p.name} justify="space-between" align="center" bg="gray.700" p={2} borderRadius="sm"><Text fontWeight="bold">{i + 1}. {p.name}</Text><Text color="orange.300">{p.score}</Text></Flex>))}</VStack></GridItem>

        {/* AI IMAGE DISPLAY */}
        <GridItem area={'image'} bg="black" borderRadius="md" display="flex" alignItems="center" justifyContent="center" p={2}><Image src={currentImageB64 || PLACEHOLDER_IMAGE} alt="AI-generated image" objectFit="contain" maxH="100%" maxW="100%" /></GridItem>

        {/* GUESS INPUT AREA */}
        <GridItem area={'guess'}><HStack as="form" onSubmit={handleGuessSubmit}><Input placeholder="Guess the prompt..." value={guess} onChange={(e) => setGuess(e.target.value)} size="lg" /><Button type="submit" colorScheme="green" size="lg" disabled={!guess.trim()}>Guess</Button></HStack></GridItem>

        {/* CHAT & GUESS HISTORY */}
        <GridItem area={'chat'} bg="gray.800" p={4} borderRadius="md" display="flex" flexDirection="column">
          <Heading size="md" mb={2}>Guess History</Heading>
          <VStack flex="1" overflowY="auto" align="stretch" gap={2} pr={2}>
            {chatMessages.map((chat, index) => (<Box key={index}><Text as="span" fontWeight="bold" color="orange.200">{chat.player}: </Text>{chat.message}</Box>))}
          </VStack>
          <Button colorScheme="red" mt={4} onClick={disconnect}>Leave Game</Button>
        </GridItem>
      </Grid>

      {/* Round End Dialog */}
      <Dialog.Root open={roomState === 'POST_ROUND'}>
          <Dialog.Content bg="gray.700">
            <Dialog.Header>{roundWinner ? `${roundWinner} Wins!` : "Time's Up!"}</Dialog.Header>
            <Dialog.Body>
              <VStack>
                <Text fontSize="lg">{roundEndReason}</Text>
                <Text>The correct prompt was:</Text>
                <Text fontWeight="bold" color="yellow.400" textAlign="center">{correctPrompt}</Text>
              </VStack>
            </Dialog.Body>
            <Dialog.Footer>
              <Text>Next round starting soon...</Text>
            </Dialog.Footer>
          </Dialog.Content>
      </Dialog.Root>
    </>
  );
}