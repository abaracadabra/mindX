// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
// Source: docs/…ERC-7857 iNFT and ERC-6551 TBA Integration.md (pragma relaxed to ^0.8.24).
pragma solidity ^0.8.24;

import {Base64} from "@openzeppelin/contracts/utils/Base64.sol";

/// @title bankon_metadata_resolver — pure-view OpenSea-compatible JSON builder
contract bankon_metadata_resolver {
    function tokenJSON(
        string memory name_,
        string memory description_,
        string memory imageURI,
        string memory animationURI,
        string memory externalURI,
        string[] memory attrKeys,
        string[] memory attrVals
    ) external pure returns (string memory) {
        bytes memory attrs = "[";
        for (uint256 i; i < attrKeys.length; ++i) {
            attrs = abi.encodePacked(
                attrs,
                i == 0 ? "" : ",",
                '{"trait_type":"', attrKeys[i], '","value":"', attrVals[i], '"}'
            );
        }
        attrs = abi.encodePacked(attrs, "]");

        bytes memory json = abi.encodePacked(
            '{"name":"', name_,
            '","description":"', description_,
            '","image":"', imageURI,
            '","animation_url":"', animationURI,
            '","external_url":"', externalURI,
            '","attributes":', attrs, '}'
        );
        return string.concat("data:application/json;base64,", Base64.encode(json));
    }
}
