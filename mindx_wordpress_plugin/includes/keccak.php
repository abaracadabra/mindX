<?php
/**
 * Pure-PHP Keccak-256 (Ethereum variant — pre-NIST sha3 with 0x01 padding).
 *
 * Single-purpose, self-contained, no external dependencies. ~120 LOC.
 * Used by includes/secp256k1.php to derive an Ethereum address from a
 * recovered public key, and by includes/class-mindx-auth-rest.php to hash
 * EIP-191 prefixed messages.
 *
 * Authoritative test vectors from the EIP-191 spec are pinned in
 * includes/secp256k1.php's self-test.
 *
 * Adapted from the public-domain reference implementation by Markku-Juhani
 * Saarinen (https://github.com/mjosaarinen/tiny_sha3) with Ethereum's
 * keccak (non-NIST) padding constant.
 *
 * License: Apache-2.0 (this port). Reference is public domain.
 */

if ( ! defined( 'ABSPATH' ) ) { exit; }

if ( ! class_exists( 'MindX_Auth_Keccak' ) ) :

class MindX_Auth_Keccak {

    /** Keccak-256 of arbitrary bytes. Returns 32 raw bytes. */
    public static function hash( $data ) {
        return self::keccak_inner( (string) $data, 1088, 512, 32, 0x01 );
    }

    /** Hex-encoded Keccak-256 (lowercase, no 0x prefix). */
    public static function hash_hex( $data ) {
        return bin2hex( self::hash( $data ) );
    }

    // ─── Core sponge / permutation ─────────────────────────────────

    private static function keccak_inner( $data, $r_bits, $c_bits, $output_bytes, $pad ) {
        $r_bytes = $r_bits / 8;
        $n = strlen( $data );
        // Pad: append 0x01, then zeros, then 0x80 at end of block.
        $blocks = (int) floor( $n / $r_bytes );
        $last_block_len = $n - ( $blocks * $r_bytes );
        $remainder = substr( $data, $blocks * $r_bytes );
        $remainder .= chr( $pad );
        $remainder = str_pad( $remainder, $r_bytes, "\x00", STR_PAD_RIGHT );
        // Set the high bit of the final byte (XOR — replace any padding).
        $remainder[ $r_bytes - 1 ] = chr( ord( $remainder[ $r_bytes - 1 ] ) | 0x80 );

        $state = array_fill( 0, 25, array( 0, 0 ) ); // 25 lanes of 64 bits (hi,lo) using 32-bit halves for PHP-int safety

        // Absorb full blocks.
        for ( $b = 0; $b < $blocks; $b++ ) {
            $offset = $b * $r_bytes;
            self::absorb_block( $state, $data, $offset, $r_bytes );
            self::keccakf( $state );
        }
        // Absorb the (padded) last block.
        self::absorb_block( $state, $remainder, 0, $r_bytes );
        self::keccakf( $state );

        // Squeeze.
        $out = '';
        $needed = $output_bytes;
        while ( $needed > 0 ) {
            for ( $i = 0; $i < 25 && $needed > 0; $i++ ) {
                $lo = $state[ $i ][1];
                $hi = $state[ $i ][0];
                for ( $j = 0; $j < 4 && $needed > 0; $j++ ) {
                    $out .= chr( ( $lo >> ( 8 * $j ) ) & 0xFF );
                    $needed--;
                }
                for ( $j = 0; $j < 4 && $needed > 0; $j++ ) {
                    $out .= chr( ( $hi >> ( 8 * $j ) ) & 0xFF );
                    $needed--;
                }
            }
            if ( $needed > 0 ) self::keccakf( $state );
        }
        return $out;
    }

    private static function absorb_block( &$state, $data, $offset, $r_bytes ) {
        for ( $i = 0; $i < $r_bytes; $i += 8 ) {
            $lane_index = $i / 8;
            $lo = ord( $data[ $offset + $i + 0 ] )
                | ( ord( $data[ $offset + $i + 1 ] ) << 8 )
                | ( ord( $data[ $offset + $i + 2 ] ) << 16 )
                | ( ord( $data[ $offset + $i + 3 ] ) << 24 );
            $hi = ord( $data[ $offset + $i + 4 ] )
                | ( ord( $data[ $offset + $i + 5 ] ) << 8 )
                | ( ord( $data[ $offset + $i + 6 ] ) << 16 )
                | ( ord( $data[ $offset + $i + 7 ] ) << 24 );
            $state[ $lane_index ][1] = $state[ $lane_index ][1] ^ ( $lo & 0xFFFFFFFF );
            $state[ $lane_index ][0] = $state[ $lane_index ][0] ^ ( $hi & 0xFFFFFFFF );
        }
    }

    /** Round constants (hi32, lo32) for the 24 rounds. */
    private static $RC = array(
        array(0x00000000, 0x00000001), array(0x00000000, 0x00008082),
        array(0x80000000, 0x0000808a), array(0x80000000, 0x80008000),
        array(0x00000000, 0x0000808b), array(0x00000000, 0x80000001),
        array(0x80000000, 0x80008081), array(0x80000000, 0x00008009),
        array(0x00000000, 0x0000008a), array(0x00000000, 0x00000088),
        array(0x00000000, 0x80008009), array(0x00000000, 0x8000000a),
        array(0x00000000, 0x8000808b), array(0x80000000, 0x0000008b),
        array(0x80000000, 0x00008089), array(0x80000000, 0x00008003),
        array(0x80000000, 0x00008002), array(0x80000000, 0x00000080),
        array(0x00000000, 0x0000800a), array(0x80000000, 0x8000000a),
        array(0x80000000, 0x80008081), array(0x80000000, 0x00008080),
        array(0x00000000, 0x80000001), array(0x80000000, 0x80008008),
    );

    /** Rotation offsets for the rho step. */
    private static $R = array(
         0,  1, 62, 28, 27,
        36, 44,  6, 55, 20,
         3, 10, 43, 25, 39,
        41, 45, 15, 21,  8,
        18,  2, 61, 56, 14,
    );

    /** Pi step permutation (where each lane goes). */
    private static $PI = array(
         0, 10, 20,  5, 15,
        16,  1, 11, 21,  6,
         7, 17,  2, 12, 22,
        23,  8, 18,  3, 13,
        14, 24,  9, 19,  4,
    );

    /** The 24-round Keccak-f[1600] permutation operating on 25 lanes of 64 bits each. */
    private static function keccakf( &$state ) {
        for ( $round = 0; $round < 24; $round++ ) {
            // θ (theta)
            $C = array();
            for ( $x = 0; $x < 5; $x++ ) {
                $C[ $x ] = array(
                    $state[ $x ][0] ^ $state[ $x + 5 ][0] ^ $state[ $x + 10 ][0] ^ $state[ $x + 15 ][0] ^ $state[ $x + 20 ][0],
                    $state[ $x ][1] ^ $state[ $x + 5 ][1] ^ $state[ $x + 10 ][1] ^ $state[ $x + 15 ][1] ^ $state[ $x + 20 ][1],
                );
            }
            for ( $x = 0; $x < 5; $x++ ) {
                $D = self::rotl1( $C[ ( $x + 1 ) % 5 ] );
                $D = array( $D[0] ^ $C[ ( $x + 4 ) % 5 ][0], $D[1] ^ $C[ ( $x + 4 ) % 5 ][1] );
                for ( $y = 0; $y < 25; $y += 5 ) {
                    $state[ $x + $y ][0] ^= $D[0];
                    $state[ $x + $y ][1] ^= $D[1];
                }
            }
            // ρ + π
            $B = array_fill( 0, 25, array( 0, 0 ) );
            for ( $i = 0; $i < 25; $i++ ) {
                $B[ self::$PI[ $i ] ] = self::rotl64( $state[ $i ], self::$R[ $i ] );
            }
            // χ (chi)
            for ( $y = 0; $y < 25; $y += 5 ) {
                for ( $x = 0; $x < 5; $x++ ) {
                    $state[ $x + $y ] = array(
                        $B[ $x + $y ][0] ^ ( ( ~ $B[ ( ( $x + 1 ) % 5 ) + $y ][0] ) & $B[ ( ( $x + 2 ) % 5 ) + $y ][0] ) & 0xFFFFFFFF,
                        $B[ $x + $y ][1] ^ ( ( ~ $B[ ( ( $x + 1 ) % 5 ) + $y ][1] ) & $B[ ( ( $x + 2 ) % 5 ) + $y ][1] ) & 0xFFFFFFFF,
                    );
                }
            }
            // ι (iota)
            $state[0][0] ^= self::$RC[ $round ][0];
            $state[0][1] ^= self::$RC[ $round ][1];
        }
    }

    private static function rotl1( $lane ) {
        return self::rotl64( $lane, 1 );
    }

    /** Rotate-left a 64-bit lane (hi32, lo32) by n bits, 0 ≤ n ≤ 63. */
    private static function rotl64( $lane, $n ) {
        $hi = $lane[0] & 0xFFFFFFFF;
        $lo = $lane[1] & 0xFFFFFFFF;
        if ( $n == 0 ) return array( $hi, $lo );
        if ( $n < 32 ) {
            return array(
                ( ( ( $hi << $n ) | self::ushr32( $lo, 32 - $n ) ) ) & 0xFFFFFFFF,
                ( ( ( $lo << $n ) | self::ushr32( $hi, 32 - $n ) ) ) & 0xFFFFFFFF,
            );
        }
        $n -= 32;
        if ( $n == 0 ) return array( $lo, $hi );
        return array(
            ( ( ( $lo << $n ) | self::ushr32( $hi, 32 - $n ) ) ) & 0xFFFFFFFF,
            ( ( ( $hi << $n ) | self::ushr32( $lo, 32 - $n ) ) ) & 0xFFFFFFFF,
        );
    }

    /** Unsigned 32-bit right shift. */
    private static function ushr32( $x, $n ) {
        if ( $n == 0 ) return $x & 0xFFFFFFFF;
        if ( $n >= 32 ) return 0;
        return ( ( $x & 0xFFFFFFFF ) >> $n ) & 0xFFFFFFFF;
    }
}

endif;
