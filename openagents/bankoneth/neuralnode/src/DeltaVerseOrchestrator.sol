// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "./BubbleRoomV4.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

contract DeltaVerseOrchestrator {
    BubbleRoomV4 public bubbleRoom;

    constructor(address bubbleRoomAddress) {
        bubbleRoom = BubbleRoomV4(bubbleRoomAddress);
    }

    function mintFromSignature(
        string memory metadataURI,
        string memory theme,
        string memory originEvent,
        address[] memory participants,
        uint8[] memory roles,
        bool isPrivate,
        bool isStable,
        bool isSoulbound,
        uint8 roomType,
        uint256 unlockTime,
        string memory storageCID,
        bool isEncryptedStorage,
        string memory aiSeed,
        string memory tone,
        bool evolves,
        bytes memory sig
    ) public {
        bytes32 hash = keccak256(abi.encodePacked(
            metadataURI,
            theme,
            originEvent,
            keccak256(abi.encodePacked(participants)),
            keccak256(abi.encodePacked(roles)),
            isPrivate,
            isStable,
            isSoulbound,
            roomType,
            unlockTime,
            storageCID,
            isEncryptedStorage,
            aiSeed,
            tone,
            evolves
        ));
        bytes32 ethHash = MessageHashUtils.toEthSignedMessageHash(hash);
        address signer = ECDSA.recover(ethHash, sig);
        require(signer == participants[0], "Invalid creator signature");

        BubbleRoomV4.Role[] memory roleEnums = new BubbleRoomV4.Role[](roles.length);
        for (uint256 i = 0; i < roles.length; i++) {
            roleEnums[i] = BubbleRoomV4.Role(roles[i]);
        }
        bubbleRoom.mintRoom(
            metadataURI,
            theme,
            originEvent,
            participants,
            roleEnums,
            isPrivate,
            isStable,
            isSoulbound,
            BubbleRoomV4.RoomType(roomType),
            unlockTime,
            storageCID,
            isEncryptedStorage,
            aiSeed,
            tone,
            evolves
        );
    }
}
