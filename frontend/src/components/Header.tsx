import { Box, Text } from "@chakra-ui/react";

export default function Header() {
  return (
    <Box as="header" w="100%" py={3} borderBottom="1px" borderColor="orange.200" textAlign="center">
      <Text fontSize="2xl" fontWeight="bold" color="orange.400" fontFamily="sans-serif">
        Pictionary <span style={{ color: '#FFA500', fontStyle: 'bold' }}>AI!</span>
      </Text>
    </Box>
  );
} 