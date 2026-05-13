<?php
/**
 * Pure-PHP secp256k1 ECDSA-recover + Ethereum address derivation.
 *
 * Single purpose: given (digest, r, s, v) recover the Ethereum address
 * that produced the signature. Used by REST/verify to authenticate the
 * caller without ever knowing their private key.
 *
 * Requires the PHP `gmp` extension (widely available on shared hosts incl.
 * Hostinger). Detects + reports cleanly if it's missing.
 *
 * Derived from the constant-folded scalar-multiplication recipe in
 *   https://www.secg.org/sec1-v2.pdf §4.1.6 (Public Key Recovery).
 * Apache-2.0.
 */

if ( ! defined( 'ABSPATH' ) ) { exit; }

if ( ! class_exists( 'MindX_Auth_Secp256k1' ) ) :

class MindX_Auth_Secp256k1 {

    /** secp256k1 curve constants (hex). */
    const P_HEX  = 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F';
    const N_HEX  = 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141';
    const GX_HEX = '79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798';
    const GY_HEX = '483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8';
    const A_HEX  = '0';     // a = 0 for secp256k1
    const B_HEX  = '7';     // b = 7

    /**
     * Verify an EIP-191 personal-sign signature.
     *
     * @param string $message            UTF-8 string that was signed (without the
     *                                   "\x19Ethereum Signed Message:\n<len>" prefix).
     * @param string $signature_hex      0x-prefixed (or not) 65-byte signature: r || s || v.
     * @param string $expected_address   0x-prefixed Ethereum address (case-insensitive).
     * @return bool|WP_Error             true if signature verifies AND the recovered
     *                                   address matches expected; WP_Error otherwise.
     */
    public static function verify_personal_sign( $message, $signature_hex, $expected_address ) {
        if ( ! extension_loaded( 'gmp' ) ) {
            return new WP_Error(
                'mindx_auth_no_gmp',
                'PHP gmp extension is required for signature verification.'
            );
        }
        $sig = self::clean_hex( $signature_hex );
        if ( strlen( $sig ) !== 130 ) {
            return new WP_Error( 'mindx_auth_bad_signature_length',
                'Signature must be 65 bytes (130 hex chars), got ' . strlen( $sig ) );
        }
        $expected = strtolower( self::clean_hex( $expected_address ) );
        if ( strlen( $expected ) !== 40 ) {
            return new WP_Error( 'mindx_auth_bad_address', 'Address must be 20 bytes (40 hex chars).' );
        }

        // EIP-191 prefixed digest.
        $prefix = "\x19" . 'Ethereum Signed Message:' . "\n" . strlen( $message );
        $digest = MindX_Auth_Keccak::hash( $prefix . $message ); // 32 raw bytes

        $r = gmp_init( substr( $sig,   0, 64 ), 16 );
        $s = gmp_init( substr( $sig,  64, 64 ), 16 );
        $v = hexdec( substr( $sig, 128, 2 ) );
        if ( $v >= 27 ) $v -= 27;
        if ( $v < 0 || $v > 3 ) {
            return new WP_Error( 'mindx_auth_bad_v', 'Recovery id v out of range: ' . $v );
        }

        $recovered = self::recover_public_key( $digest, $r, $s, $v );
        if ( is_wp_error( $recovered ) ) return $recovered;

        // Ethereum address = last 20 bytes of keccak256(uncompressed_pubkey_x||y).
        $addr_full = MindX_Auth_Keccak::hash( $recovered );
        $addr_hex  = strtolower( bin2hex( substr( $addr_full, -20 ) ) );

        return hash_equals( $addr_hex, $expected );
    }

    // ─── Public-key recovery (SEC1 §4.1.6) ─────────────────────────

    private static function recover_public_key( $digest_bytes, $r, $s, $v ) {
        $p = gmp_init( self::P_HEX, 16 );
        $n = gmp_init( self::N_HEX, 16 );
        $e = gmp_init( bin2hex( $digest_bytes ), 16 );

        // x = r + (v // 2) * n   (j = 0 for v in {0,1}; v=2,3 imply x >= n)
        $j = (int) floor( $v / 2 );
        $x = gmp_add( $r, gmp_mul( gmp_init( $j ), $n ) );
        if ( gmp_cmp( $x, $p ) >= 0 ) {
            return new WP_Error( 'mindx_auth_x_out_of_range', 'Recovered x is outside field.' );
        }

        // y^2 = x^3 + 7  (mod p)
        $alpha = gmp_mod( gmp_add( gmp_powm( $x, gmp_init( 3 ), $p ), gmp_init( 7 ) ), $p );
        $y     = gmp_powm( $alpha, gmp_div_q( gmp_add( $p, gmp_init( 1 ) ), gmp_init( 4 ) ), $p );
        // Pick the y with the correct parity (low bit matches (v & 1)).
        $y_parity = gmp_intval( gmp_mod( $y, gmp_init( 2 ) ) );
        if ( $y_parity !== ( $v & 1 ) ) {
            $y = gmp_sub( $p, $y );
        }
        $R = array( $x, $y );

        // Q = r^-1 (sR - eG)  (mod n)
        $r_inv  = gmp_invert( $r, $n );
        if ( $r_inv === false ) {
            return new WP_Error( 'mindx_auth_r_not_invertible', 'r is not invertible mod n.' );
        }
        $sR     = self::point_mul( $s, $R, $p );
        $eG     = self::point_mul( $e, array( gmp_init( self::GX_HEX, 16 ), gmp_init( self::GY_HEX, 16 ) ), $p );
        $sR_minus_eG = self::point_add( $sR, self::point_negate( $eG, $p ), $p );
        $Q      = self::point_mul( $r_inv, $sR_minus_eG, $p );
        if ( $Q === null ) {
            return new WP_Error( 'mindx_auth_recovery_failed', 'Could not recover public key.' );
        }

        // Encode as uncompressed (x || y), 64 bytes, no 0x04 prefix
        // because Ethereum's keccak takes the raw concatenation.
        $x_hex = str_pad( gmp_strval( $Q[0], 16 ), 64, '0', STR_PAD_LEFT );
        $y_hex = str_pad( gmp_strval( $Q[1], 16 ), 64, '0', STR_PAD_LEFT );
        return hex2bin( $x_hex . $y_hex );
    }

    // ─── EC point arithmetic over Fp ───────────────────────────────

    /** Point at infinity sentinel. */
    private static function is_infinity( $P ) {
        return $P === null;
    }

    private static function point_negate( $P, $p ) {
        if ( self::is_infinity( $P ) ) return null;
        return array( $P[0], gmp_mod( gmp_sub( $p, $P[1] ), $p ) );
    }

    private static function point_add( $P, $Q, $p ) {
        if ( self::is_infinity( $P ) ) return $Q;
        if ( self::is_infinity( $Q ) ) return $P;
        if ( gmp_cmp( $P[0], $Q[0] ) === 0 ) {
            if ( gmp_cmp( $P[1], $Q[1] ) === 0 ) {
                return self::point_double( $P, $p );
            }
            return null; // P + (-P) = O
        }
        $lambda = gmp_mod(
            gmp_mul(
                gmp_sub( $Q[1], $P[1] ),
                gmp_invert( gmp_mod( gmp_sub( $Q[0], $P[0] ), $p ), $p )
            ),
            $p
        );
        $x3 = gmp_mod( gmp_sub( gmp_sub( gmp_mul( $lambda, $lambda ), $P[0] ), $Q[0] ), $p );
        $y3 = gmp_mod( gmp_sub( gmp_mul( $lambda, gmp_sub( $P[0], $x3 ) ), $P[1] ), $p );
        return array( $x3, $y3 );
    }

    private static function point_double( $P, $p ) {
        if ( self::is_infinity( $P ) ) return null;
        if ( gmp_cmp( $P[1], gmp_init( 0 ) ) === 0 ) return null;
        $two = gmp_init( 2 );
        $three = gmp_init( 3 );
        $lambda = gmp_mod(
            gmp_mul(
                gmp_mul( $three, gmp_mul( $P[0], $P[0] ) ),
                gmp_invert( gmp_mod( gmp_mul( $two, $P[1] ), $p ), $p )
            ),
            $p
        );
        $x3 = gmp_mod( gmp_sub( gmp_mul( $lambda, $lambda ), gmp_mul( $two, $P[0] ) ), $p );
        $y3 = gmp_mod( gmp_sub( gmp_mul( $lambda, gmp_sub( $P[0], $x3 ) ), $P[1] ), $p );
        return array( $x3, $y3 );
    }

    /** Double-and-add. */
    private static function point_mul( $k, $P, $p ) {
        $result = null;
        $addend = $P;
        $k_str  = gmp_strval( $k, 2 );
        for ( $i = strlen( $k_str ) - 1; $i >= 0; $i-- ) {
            if ( $k_str[ $i ] === '1' ) {
                $result = self::point_add( $result, $addend, $p );
            }
            $addend = self::point_double( $addend, $p );
        }
        return $result;
    }

    // ─── Helpers ───────────────────────────────────────────────────

    public static function clean_hex( $s ) {
        $s = ltrim( strtolower( (string) $s ) );
        if ( substr( $s, 0, 2 ) === '0x' ) $s = substr( $s, 2 );
        return $s;
    }
}

endif;
