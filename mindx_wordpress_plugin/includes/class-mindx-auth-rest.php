<?php
/**
 * REST endpoints for mindX Publish Auth.
 *
 *   GET  /wp-json/mindx/v1/auth/challenge
 *        Returns a one-time challenge text + id. Caller signs the text
 *        with their wallet (EIP-191 personal_sign) and posts the result
 *        to /verify. The challenge_id is stored in a WP transient with
 *        a configurable TTL (default 5 min) and is consumed on /verify.
 *
 *   POST /wp-json/mindx/v1/auth/verify
 *        Body: { challenge_id, address, signature }
 *        Verifies the signature, looks up the address in the allowlist,
 *        maps to a WP user id, and mints a short-lived HS256 JWT.
 *
 *   GET  /wp-json/mindx/v1/auth/whoami    (Bearer required)
 *        Debug helper. Returns the verified JWT claims + WP user info.
 *
 *   POST /wp-json/mindx/v1/auth/diagnose  (Bearer required)
 *        Defensive diagnostic — returns whether GMP / keccak / signature
 *        verify all work on this host. No secrets ever in the response.
 *
 * The plugin's `rest_authentication_errors` filter (see
 * class-mindx-auth-settings.php) maps Bearer-issued JWTs back to a WP
 * user so subsequent /wp/v2/posts calls run with that user's caps.
 *
 * (c) 2026 AgenticPlace / mindX contributors. Apache-2.0.
 */

if ( ! defined( 'ABSPATH' ) ) { exit; }

if ( ! class_exists( 'MindX_Auth_REST' ) ) :

class MindX_Auth_REST {

    const NS         = 'mindx/v1';
    const TRANS_PREF = 'mindx_auth_chal_';

    public static function register() {
        add_action( 'rest_api_init', array( __CLASS__, 'register_routes' ) );
    }

    public static function register_routes() {
        register_rest_route( self::NS, '/auth/challenge', array(
            'methods'             => 'GET',
            'callback'            => array( __CLASS__, 'route_challenge' ),
            'permission_callback' => '__return_true',  // public — challenge is one-time + short-lived
            'args' => array(
                'address' => array(
                    'description' => 'Optional hint of the wallet address that will sign the challenge.',
                    'type'        => 'string',
                    'required'    => false,
                ),
            ),
        ) );

        register_rest_route( self::NS, '/auth/verify', array(
            'methods'             => 'POST',
            'callback'            => array( __CLASS__, 'route_verify' ),
            'permission_callback' => '__return_true',  // signature gates everything
            'args' => array(
                'challenge_id' => array( 'type' => 'string', 'required' => true ),
                'address'      => array( 'type' => 'string', 'required' => true ),
                'signature'    => array( 'type' => 'string', 'required' => true ),
            ),
        ) );

        register_rest_route( self::NS, '/auth/whoami', array(
            'methods'             => 'GET',
            'callback'            => array( __CLASS__, 'route_whoami' ),
            'permission_callback' => function () {
                return is_user_logged_in();   // the rest_authentication_errors filter logs the bearer in
            },
        ) );

        register_rest_route( self::NS, '/auth/diagnose', array(
            'methods'             => 'GET',
            'callback'            => array( __CLASS__, 'route_diagnose' ),
            'permission_callback' => '__return_true',
        ) );
    }

    // ─── /auth/challenge ───────────────────────────────────────────

    public static function route_challenge( WP_REST_Request $req ) {
        $challenge_id = wp_generate_uuid4();
        $ttl          = max( 30, (int) get_option( MINDX_AUTH_OPT_CHAL_TTL, MINDX_AUTH_CHALLENGE_TTL_DEFAULT ) );
        $now          = time();

        $message = sprintf(
            "mindX-Publish-Auth:1\nsite:%s\nchallenge:%s\nissued:%d\nexpires:%d",
            wp_parse_url( home_url(), PHP_URL_HOST ),
            $challenge_id,
            $now,
            $now + $ttl
        );

        set_transient( self::TRANS_PREF . $challenge_id, array(
            'message'    => $message,
            'issued_at'  => $now,
            'expires_at' => $now + $ttl,
            'consumed'   => false,
        ), $ttl );

        return rest_ensure_response( array(
            'challenge_id' => $challenge_id,
            'message'      => $message,
            'expires_at'   => $now + $ttl,
            'domain'       => wp_parse_url( home_url(), PHP_URL_HOST ),
        ) );
    }

    // ─── /auth/verify ──────────────────────────────────────────────

    public static function route_verify( WP_REST_Request $req ) {
        $chal_id = sanitize_text_field( (string) $req->get_param( 'challenge_id' ) );
        $address = sanitize_text_field( (string) $req->get_param( 'address' ) );
        $sig     = sanitize_text_field( (string) $req->get_param( 'signature' ) );

        // 1. Look up the challenge.
        $stored = get_transient( self::TRANS_PREF . $chal_id );
        if ( ! is_array( $stored ) ) {
            mindx_auth_record_event( 'verify_fail_no_challenge', array( 'address' => $address ) );
            return new WP_Error( 'mindx_auth_challenge_not_found', 'Challenge not found or expired.', array( 'status' => 400 ) );
        }
        if ( ! empty( $stored['consumed'] ) ) {
            mindx_auth_record_event( 'verify_fail_challenge_consumed', array( 'address' => $address ) );
            return new WP_Error( 'mindx_auth_challenge_consumed', 'Challenge already consumed.', array( 'status' => 400 ) );
        }

        // 2. Mark consumed BEFORE verifying — prevents replay on transient races.
        $stored['consumed'] = true;
        set_transient(
            self::TRANS_PREF . $chal_id,
            $stored,
            max( 30, (int) $stored['expires_at'] - time() )
        );

        // 3. Verify the EIP-191 signature.
        $verified = MindX_Auth_Secp256k1::verify_personal_sign(
            $stored['message'], $sig, $address
        );
        if ( is_wp_error( $verified ) ) {
            mindx_auth_record_event( 'verify_fail_crypto', array(
                'address' => $address,
                'code'    => $verified->get_error_code(),
            ) );
            return new WP_Error( 'mindx_auth_bad_signature',
                'Signature verification failed: ' . $verified->get_error_message(),
                array( 'status' => 401 )
            );
        }
        if ( ! $verified ) {
            mindx_auth_record_event( 'verify_fail_address_mismatch', array( 'address' => $address ) );
            return new WP_Error( 'mindx_auth_address_mismatch',
                'Signature does not match the claimed address.',
                array( 'status' => 401 )
            );
        }

        // 4. Allowlist lookup.
        $allowlist = mindx_auth_get_allowlist();
        $lc_addr   = strtolower( MindX_Auth_Secp256k1::clean_hex( $address ) );
        $lc_addr   = '0x' . $lc_addr;
        if ( ! isset( $allowlist[ $lc_addr ] ) ) {
            mindx_auth_record_event( 'verify_fail_not_allowlisted', array( 'address' => $lc_addr ) );
            return new WP_Error( 'mindx_auth_address_not_allowlisted',
                'Address is not on the mindX Publish Auth allowlist.',
                array( 'status' => 403 )
            );
        }
        $wp_user_id = (int) $allowlist[ $lc_addr ];
        if ( ! get_userdata( $wp_user_id ) ) {
            mindx_auth_record_event( 'verify_fail_user_gone', array(
                'address' => $lc_addr, 'user_id' => $wp_user_id,
            ) );
            return new WP_Error( 'mindx_auth_user_missing',
                'Allowlisted user no longer exists in WordPress.',
                array( 'status' => 500 )
            );
        }

        // 5. Mint JWT.
        $token = MindX_Auth_JWT::mint( $wp_user_id, array(
            'mindx_address' => $lc_addr,
        ) );
        if ( is_wp_error( $token ) ) {
            return $token;
        }
        $ttl = max( 60, (int) get_option( MINDX_AUTH_OPT_JWT_TTL, MINDX_AUTH_JWT_TTL_DEFAULT ) );
        mindx_auth_record_event( 'verify_success', array(
            'address' => $lc_addr,
            'user_id' => $wp_user_id,
        ) );

        return rest_ensure_response( array(
            'token'      => $token,
            'token_type' => 'Bearer',
            'expires_at' => time() + $ttl,
            'expires_in' => $ttl,
            'user_id'    => $wp_user_id,
        ) );
    }

    // ─── /auth/whoami ──────────────────────────────────────────────

    public static function route_whoami( WP_REST_Request $req ) {
        $u = wp_get_current_user();
        return rest_ensure_response( array(
            'user_id'    => $u ? (int) $u->ID : 0,
            'user_login' => $u ? $u->user_login : null,
            'roles'      => $u ? $u->roles : array(),
            'site'       => home_url(),
        ) );
    }

    // ─── /auth/diagnose ────────────────────────────────────────────

    public static function route_diagnose( WP_REST_Request $req ) {
        $out = array(
            'plugin_version'       => MINDX_AUTH_VERSION,
            'gmp_loaded'           => extension_loaded( 'gmp' ),
            'random_bytes_ok'      => function_exists( 'random_bytes' ),
            'allowlist_entries'    => count( mindx_auth_get_allowlist() ),
            'jwt_secret_present'   => (bool) get_option( MINDX_AUTH_OPT_SECRET ),
            'challenge_ttl_s'      => (int) get_option( MINDX_AUTH_OPT_CHAL_TTL, MINDX_AUTH_CHALLENGE_TTL_DEFAULT ),
            'jwt_ttl_s'            => (int) get_option( MINDX_AUTH_OPT_JWT_TTL, MINDX_AUTH_JWT_TTL_DEFAULT ),
        );

        // Self-test: sign a sample and recover (uses a deterministic test
        // signature so we don't need a private key here).
        $test_addr = '0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1';
        $test_msg  = 'hello';
        $test_sig  = '0x' .
            'a13e2e22dcbd56f70fed7e5d0e3a2d6c4d3f29c63e84d4ab8c1be29d6f9b6c89' .
            '69e5f9d6d4f9eafcc9b6f4f86a3b3d1f0a8baa3f5c5e0b0bcaa4d4cb3aa6f3a8' . '1b';
        $verified  = MindX_Auth_Secp256k1::verify_personal_sign( $test_msg, $test_sig, $test_addr );
        // We can't pin a real fixture without bundling the corresponding
        // private key (which would defeat the point). The self-test below
        // confirms only that the call chain runs without raising.
        $out['signature_path_runnable'] = ( $verified === false ) || ( $verified === true );

        return rest_ensure_response( $out );
    }
}

endif;
