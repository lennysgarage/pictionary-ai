// src/components/GameRoom.tsx
import {
    Box, Button, VStack, Text, Input, HStack, Grid, GridItem,
    Heading, Progress, Flex, Spacer, Image // Image is now a key component
  } from "@chakra-ui/react";
  import { useParams, useNavigate } from "react-router-dom";
  import { useState } from "react";
  
  // A sample 1x1 transparent pixel in Base64. Replace with a loading spinner or placeholder.
  const PLACEHOLDER_IMAGE = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";
  
  // MOCK DATA REVISED for the new game logic
  const MOCK_GAME_STATE = {
    round: 3,
    totalRounds: 10,
    timeLeft: 45,
    totalTime: 60,
    // The server sends the image as a Base64 string
    imageBase64: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAARTSURBVHhe7ZxNaxNRFIbfzCQSMRKkbhUEH3pQUUhB0YMiIq4EXHWhp/8CgqAFLy7d+A+4cCEoSKKIi4I/iig+9KAiKCIiEmli0iRJJJPMvL7HhGCSSTfzzh3vnsm959yZe3JmggZNWu1/49Vf/t3wwrOrfVp87/F6/X39rK/vD6lP/+u+P1TfPVyfPq2/etx/Sj3/yP7U/vXb/af0s7M/VZ8+V98+Xl+d/V19/2l9eXb/af209A/VZ49V17t/qV+fP1Zf/vXn/Vv6Vb/S3/5K/dGv9Mv/qT/8z/37/u3/2B/aV/8+/W59+/z+tv6e/Vn9+n713fO1/aP63fO1++bZ/bX6vfdP6vfnT+sPz5+vPz5/ur5//7z+UP39g/qt86f1e+fP6/fOn9fvPz+r3z+/vz9Wv3/+sH5v/Wl99vz+/mP1w+tP69fvX9ev3r+uX71/Xr96/7p+9f51/fr9S/r9+5f1+/cv6/fvX9fv37+s379/Wb9//7J+///l/f39y/r9/Zf1+/sv6/f3X9bv77+s399/Wb+///I+f/9l/f7+y/r9/Zf1+/sv6/f3X9bv77+s399/Wb+///K+f/+yfv/+Zf3+/sv6/f2X9fv7L+v391/W7++/rN/ff1m/v/+yfn//Zf3+/sv6/f2X9fv7L+v391/W7++/rN/ff1nff/+yfv/+Zf3+/sv6/f2X9fv7L+v391/W7++/rN/ff1nff/+yfn//Zf3+/sv6/f2X9fv7L+v391/W7++/rN/ff1m/v/+yfn//Zf3+/sv6/f2X9fv7L+v391/W7++/rN/ff1nff/+yfv/+Zf3+/sv6/f2X9fv7L+v391/W7++/rN/ff1m/v/+yfn//Zf3+/sv6/f2X9fv7L+v391/W7++/rN/ff1nff/+yfv/+Zf3+/sv6/f2X9fv7L+v391/W7++/rN/ff1nff/+yfn//Zf3+/sv6/f2X9fv7L+v391/W7++/rN/ff1m/v/+yfn//Zf3+/sv6/f2X9fv7L+v391/W7++/rN/ff1nff/+yfv/+Zf3+/sv6/f2X9fv7L+v391/W7++/rN/ff1nff/+yfn//Zf3+/sv6/f2X9fv7L+v391/W7++/rN/ff1m/v/+yfn//Zf3+/sv6/f2X9fv7L+v391/W7++/rN/ff1nff/+yfn//Zf3+/sv6/f2X9fv7L+v391/W7++/rN/ff1m/v/+yfn//Zf3+/sv6/f2X9fv7L+v391/W7++/rN/ff1nff/+yfv/+Zf3+/sv6/f2X9fv7L+v391/W7++/rN/ff1nff/+yfn//Zf3+/sv6/f2X9fv7L+v391/W7++/rN/ff1m/v/+yfn//Zf3+/sv6/f2X9fv7L+v391/W7++/rN/ff1nff/+yfv/+Zf3+/sv6/f2X9fv7L+v391/W7++/rN/ff1m/v/+yfn//Zf3+/sv6/f2X9fv7L+v391/W7++/rN/ff1nff/+yfv/+Zf3+/sv6/f2X9fv7L+v391/W7++/rN/ff1nff/+yfv//Zf3+/st/vH5t3X/af23dv24/+Pj/b/iJk1baL/sD+0kXXb4WAAAAAElFTkSuQmCC",
    // A hint about the prompt structure
    promptHint: "Phrase, 4 words",
    players: [
      { name: "You", score: 1250 },
      { name: "Arturo", score: 968 },
      { name: "Beatrice", score: 800 },
      { name: "Carlos", score: 750 },
    ],
    // Chat now shows full prompt guesses
    chat: [
      { player: "Beatrice", message: "A cat playing chess" },
      { player: "Carlos", message: "Robot painting a sunset" },
      { player: "Arturo", message: "Cosmic owl in space" },
    ],
  };
  
  export default function GameRoom() {
    const { roomId } = useParams();
    const navigate = useNavigate();
    const [guess, setGuess] = useState("");
    const [currentImage, setCurrentImage] = useState(PLACEHOLDER_IMAGE);
  
    // In a real app, a WebSocket message would trigger this update
    useState(() => {
      // Simulate loading the image from the server
      setTimeout(() => {
        setCurrentImage(MOCK_GAME_STATE.imageBase64);
      }, 1000); // 1s delay to simulate loading
    });
  
    const sortedPlayers = MOCK_GAME_STATE.players.sort((a, b) => b.score - a.score);
  
    const handleGuessSubmit = () => {
      if (!guess.trim()) return;
      // TODO: Send guess to WebSocket server
      console.log(`Guessing: ${guess}`);
      // Add the guess to the chat for immediate feedback (the server would normally do this)
      MOCK_GAME_STATE.chat.push({ player: "You", message: guess });
      setGuess("");
    };
  
    return (
      <Grid
        templateAreas={`"header header header"
                        "players image chat"
                        "players guess chat"`}
        gridTemplateRows={'auto 1fr auto'}
        gridTemplateColumns={'250px 1fr 300px'}
        h="calc(100vh - 160px)"
        w="100%"
        gap='4'
      >
        {/* HEADER AREA */}
        <GridItem area={'header'} bg="gray.700" p={2} borderRadius="md">
          <Flex align="center">
            <Box>
              <Text>Round {MOCK_GAME_STATE.round}/{MOCK_GAME_STATE.totalRounds}</Text>
              {/* <Progress value={(MOCK_GAME_STATE.timeLeft / MOCK_GAME_STATE.totalTime) * 100} colorScheme="orange" size="sm" /> */}
            </Box>
            <Spacer />
            <Heading size="lg" color="yellow.400">
              {MOCK_GAME_STATE.promptHint}
            </Heading>
            <Spacer />
            <Text fontSize="2xl" fontWeight="bold">{MOCK_GAME_STATE.timeLeft}s</Text>
          </Flex>
        </GridItem>
  
        {/* PLAYER LIST / SCOREBOARD */}
        <GridItem area={'players'} bg="gray.800" p={4} borderRadius="md">
          <VStack align="stretch" gap={3}>
            <Heading size="md" mb={2}>Scoreboard</Heading>
            {sortedPlayers.map((player, index) => (
              <Flex key={index} justify="space-between" align="center" bg="gray.700" p={2} borderRadius="sm">
                <Text fontWeight={player.name === "You" ? "bold" : "normal"}>
                  {index + 1}. {player.name}
                </Text>
                <Text color="orange.300">{player.score}</Text>
              </Flex>
            ))}
          </VStack>
        </GridItem>
  
        {/* AI IMAGE DISPLAY */}
        <GridItem area={'image'} bg="black" borderRadius="md" display="flex" alignItems="center" justifyContent="center" p={2}>
          <Image
            src={currentImage}
            alt="AI-generated image to guess"
            objectFit="contain"
            maxH="100%"
            maxW="100%"
          />
        </GridItem>
  
        {/* GUESS INPUT AREA */}
        <GridItem area={'guess'}>
          <HStack as="form" onSubmit={(e) => { e.preventDefault(); handleGuessSubmit(); }}>
            <Input
              placeholder="Guess the prompt..."
              value={guess}
              onChange={(e) => setGuess(e.target.value)}
              size="lg"
            />
            <Button type="submit" colorScheme="green" size="lg" disabled={!guess.trim()}>Guess</Button>
          </HStack>
        </GridItem>
  
        {/* CHAT & GUESS HISTORY */}
        <GridItem area={'chat'} bg="gray.800" p={4} borderRadius="md" display="flex" flexDirection="column">
          <Heading size="md" mb={2}>Guess History</Heading>
          <VStack flex="1" overflowY="auto" align="stretch" gap={2} pr={2} 
            css={{ '&::-webkit-scrollbar': { width: '4px' }, '&::-webkit-scrollbar-track': { width: '6px' }, '&::-webkit-scrollbar-thumb': { background: '#FFC107', borderRadius: '24px' } }}>
            {MOCK_GAME_STATE.chat.map((chat, index) => (
              <Box key={index}><Text as="span" fontWeight="bold" color="orange.200">{chat.player}: </Text>{chat.message}</Box>
            ))}
          </VStack>
          <Button colorScheme="red" mt={4} onClick={() => navigate("/")}>Leave Game</Button>
        </GridItem>
      </Grid>
    );
  }