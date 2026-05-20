<?php
/**
 * Minimal HS256 JWT mint + verify for the mindX Publish Auth plugin.
 * No vendored libraries — single-purpose, ~80 LOC, easy to audit.
 *
 * (c) 2026 AgenticPlace / mindX contributors. Apache-2.0.
 */

if ( ! defined( 'ABSPATH' ) ) { exit; }

if ( ! class_exists( 'MindX_Auth_JWT' ) ) :

class MindX_Auth_JWT {

    /** Mint an HS256 JWT for the given WP user with the configured TTL. */
    public static function mint( $user_id, $extra_claims = array() ) {
        $secret = self::secret();
        if ( ! $secret ) return new WP_Error( 'mindx_auth_no_secret', 'JWT secret not configured.' );
        $ttl   = (int) get_option( MINDX_AUTH_OPT_JWT_TTL, MINDX_AUTH_JWT_TTL_DEFAULT );
        $now   = time();
        $iss   = home_url();
        $payload = array_merge(
            array(
                'iss' => $iss,
                'aud' => 'mindx-publish-auth',
                'sub' => (int) $user_id,
                'iat' => $now,
                'nbf' => $now,
                'exp' => $now + max( 60, $ttl ),
                'jti' => bin2hex( random_bytes( 12 ) ),
            ),
            (array) $extra_claims
        );
        return self::encode( $payload, $secret );
    }

    /**
     * Verify a JWT. Returns the payload array on success, or a WP_Error on
     * failure. Errors carry a stable code so the REST filter can decide
     * whether to surface them.
     */
    public static function verify( $token ) {
        $secret = self::secret();
        if ( ! $secret ) return new WP_Error( 'mindx_auth_no_secret', 'JWT secret not configured.' );

        $parts = explode( '.', (string) $token );
        if ( count( $parts ) !== 3 ) {
            return new WP_Error( 'mindx_auth_jwt_malformed', 'JWT must have three segments.' );
        }
        list( $h64, $p64, $s64 ) = $parts;

        $header = json_decode( self::b64u_decode( $h64 ), true );
        if ( ! is_array( $header ) || ( $header['alg'] ?? '' ) !== 'HS256' ) {
            return new WP_Error( 'mindx_auth_jwt_bad_alg', 'JWT alg must be HS256.' );
        }
        $signing_input = $h64 . '.' . $p64;
        $expected      = self::b64u_encode( hash_hmac( 'sha256', $signing_input, $secret, true ) );
        if ( ! hash_equals( $expected, $s64 ) ) {
            return new WP_Error( 'mindx_auth_jwt_bad_sig', 'JWT signature does not verify.' );
        }
        $payload = json_decode( self::b64u_decode( $p64 ), true );
        if ( ! is_array( $payload ) ) {
            return new WP_Error( 'mindx_auth_jwt_bad_payload', 'JWT payload is not JSON.' );
        }
        $now = time();
        if ( isset( $payload['nbf'] ) && $now + 5 < (int) $payload['nbf'] ) {
            return new WP_Error( 'mindx_auth_jwt_not_yet_valid', 'JWT not yet valid (nbf in the future).' );
        }
        if ( isset( $payload['exp'] ) && $now >= (int) $payload['exp'] ) {
            return new WP_Error( 'mindx_auth_jwt_expired', 'JWT has expired.' );
        }
        if ( ( $payload['aud'] ?? '' ) !== 'mindx-publish-auth' ) {
            return new WP_Error( 'mindx_auth_jwt_wrong_aud', 'JWT aud is not mindx-publish-auth.' );
        }
        if ( empty( $payload['sub'] ) || ! is_int( $payload['sub'] ) ) {
            return new WP_Error( 'mindx_auth_jwt_no_sub', 'JWT has no integer sub.' );
        }
        return $payload;
    }

    // ─── helpers ──────────────────────────────────────────────────

    private static function secret() {
        $v = get_option( MINDX_AUTH_OPT_SECRET );
        return is_string( $v ) && strlen( $v ) >= 32 ? $v : '';
    }

    private static function encode( $payload, $secret ) {
        $h64 = self::b64u_encode( wp_json_encode( array( 'alg' => 'HS256', 'typ' => 'JWT' ) ) );
        $p64 = self::b64u_encode( wp_json_encode( $payload ) );
        $sig = hash_hmac( 'sha256', $h64 . '.' . $p64, $secret, true );
        return $h64 . '.' . $p64 . '.' . self::b64u_encode( $sig );
    }

    private static function b64u_encode( $data ) {
        return rtrim( strtr( base64_encode( $data ), '+/', '-_' ), '=' );
    }

    private static function b64u_decode( $data ) {
        $pad = strlen( $data ) % 4;
        if ( $pad ) $data .= str_repeat( '=', 4 - $pad );
        return base64_decode( strtr( $data, '-_', '+/' ) );
    }

    /** Rotate the HS256 secret. Returns the new secret (caller logs the rotation). */
    public static function rotate_secret() {
        $new = bin2hex( random_bytes( 32 ) );
        update_option( MINDX_AUTH_OPT_SECRET, $new, false );
        return $new;
    }
}

endif;
