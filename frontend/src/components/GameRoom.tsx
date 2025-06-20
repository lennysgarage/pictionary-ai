// src/components/GameRoom.tsx
import { Box, Button, VStack, Text, Input, HStack, Flex, Heading, Image } from "@chakra-ui/react";
import { useState, useEffect } from "react";
import { useGame } from "@/contexts/GameContext";
import Footer from "./Footer";

const PLACEHOLDER_IMAGE = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";

export default function GameRoom() {
  const { gameState, sendMessage, disconnect } = useGame();
  const { players, currentRound, totalRounds, timeLeft, promptHint, currentImageB64, correctPrompt, similarity, gameState: roomState } = gameState;

  const [guess, setGuess] = useState("");
  const [timer, setTimer] = useState(timeLeft);

  useEffect(() => {
    setTimer(timeLeft);
    if (timeLeft <= 0) return;

    const interval = setInterval(() => {
      setTimer(prev => (prev > 0 ? prev - 1 : 0));
    }, 1000);

    return () => clearInterval(interval);
  }, [timeLeft, currentRound]);

  const handleGuessSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!guess.trim()) return;
    sendMessage("new_guess", { guess });
    setGuess("");
  };

  const sortedPlayers = [...players].sort((a, b) => b.score - a.score);
  const topScore = sortedPlayers[0]?.score || 1;

  return (
    <Flex direction="column" minH="100vh" w="100%" bg="gray.900">
      {/* HEADER */}
      <Box as="header" w="100%" py={2} px={6} bg="gray.800" borderRadius="md" mt={4} mb={2} boxShadow="md">
        <Flex align="center" justify="space-between">
          <Box bg="blue.700" px={4} py={1} borderRadius="md">
            <Text color="white" fontWeight="bold">Round {currentRound}/{totalRounds} - {timer.toString().padStart(2, '0')}s</Text>
          </Box>
          <Button variant="surface" colorPalette="red" onClick={disconnect}>Leave</Button>
        </Flex>
      </Box>

      {/* MAIN CONTENT */}
      <Flex flex={1} w="100%" maxW="1100px" mx="auto" gap={8}>
        {/* IMAGE LEFT */}
        <Box flex="1.2" bg="black" borderRadius="md" display="flex" alignItems="center" justifyContent="center" minH="420px" maxH="520px" my={4}>
          <Image src={currentImageB64 || PLACEHOLDER_IMAGE} alt="AI-generated image" objectFit="contain" maxH="95%" maxW="95%" borderRadius="md" />
        </Box>

        {/* RIGHT SIDE: SCOREBOARD + GUESS */}
        <Flex flex="1" direction="column" gap={6} justify="flex-start" mt={4}>
          {/* SCOREBOARD */}
          <Box bg="gray.800" borderRadius="md" p={4} boxShadow="md">
            <Heading size="sm" mb={3} color="blue.200">Scoreboard</Heading>
            <VStack align="stretch" gap={2}>
              {sortedPlayers.map((p, i) => {
                const percent = topScore ? Math.round((p.score / topScore) * 100) : 0;
                return (
                  <Flex key={p.name} align="center" justify="space-between" bg="gray.700" p={2} borderRadius="sm" borderLeftWidth={3} borderLeftColor={i === 0 ? 'yellow.400' : 'gray.600'}>
                    <Text fontWeight="bold">{i + 1}st: {p.name}</Text>
                    <Text color="blue.200" fontSize="sm">{percent}%</Text>
                    <Text color="orange.300" fontWeight="bold">({p.score})</Text>
                  </Flex>
                );
              })}
            </VStack>
          </Box>

          {/* GUESS INPUT */}
          <Box bg="gray.700" borderRadius="md" p={4}>
            <form onSubmit={handleGuessSubmit}>
              <HStack>
                <Text color="orange.200" fontWeight="bold">Guess:</Text>
                <Input placeholder="Type your guess..." value={guess} onChange={(e) => setGuess(e.target.value)} size="md" bg="white" color="black" _placeholder={{ color: 'gray.500' }} />
                <Button type="submit" colorScheme="orange" disabled={!guess.trim()}>Guess</Button>
              </HStack>
            </form>

            {similarity !== 0 && (
              <Box mt={3} p={2} bg="gray.800" borderRadius="md" textAlign="center">
                <Text color="yellow.300" fontWeight="bold">
                  {`Similarity: ${similarity.toFixed(2)}%`}
                </Text>
              </Box>
            )}
          </Box>
        </Flex>
      </Flex>

      {/* Round End Message */}
      {roomState === 'POST_ROUND' && (
        <Box position="fixed" top="0" left="0" w="100vw" h="100vh" bg="blackAlpha.700" display="flex" alignItems="center" justifyContent="center" zIndex={1000}>
          <Box bg="gray.700" p={8} borderRadius="lg" boxShadow="2xl" minW="340px">
            <Text>The correct prompt was:</Text>
            <Text fontWeight="bold" color="yellow.400" textAlign="center" mb={4}>{correctPrompt}</Text>
            <Text color="gray.300">Next round starting soon...</Text>
          </Box>
        </Box>
      )}

      {/* FOOTER */}
      <Footer />
    </Flex>
  );
}