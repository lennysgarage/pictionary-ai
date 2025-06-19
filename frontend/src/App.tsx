import { Box, Flex } from "@chakra-ui/react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Lobby from "./components/Lobby";
import GameRoom from "./components/GameRoom";
import RoomJoinCreate from "./components/RoomJoinCreate";
import Header from "./components/Header";
import Footer from "./components/Footer";

function App() {
  return (
    <Router>
      <Box height="80px">
        <Header />
      </Box>
      <Box as="main" minH="80vh" display="flex" alignItems="center" justifyContent="center">
        <Routes>
          <Route path="/" element={<RoomJoinCreate />} />
          <Route path="/lobby/:roomId" element={<Lobby />} />
          <Route path="/game/:roomId" element={<GameRoom />} />
        </Routes>
      </Box>
      <Box height="40px" position={"absolute"} bottom="0" left="0" right="0">
        <Footer />
      </Box>
    </Router>
  );
}

export default App;
