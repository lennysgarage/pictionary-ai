import { Box, Flex, Link, Image } from "@chakra-ui/react";
import githubLogo from "../assets/github.png"

export default function Footer() {
  return (
    <Box
    height="40px"
    bg="#14181c"
    color={"#f4fcf0"}
>
    <Flex
        justify="center"
        align={"center"}
        height={"100%"}
    >
        {/* Github */}
        <Link href="https://github.com/lennysgarage" target="_blank" _hover={{
            color: '#00b020',
        }}>
            <Flex align="center" gap={2}>
                <Image src={githubLogo} alt="Github" boxSize="28px" />
                My Github
            </Flex>
        </Link>
    </Flex>
</Box>
  );
} 