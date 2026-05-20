<?php
/**
 * Plugin Name:       mindX Publish Auth
 * Plugin URI:        https://mindx.pythai.net
 * Description:       Wallet-signature authentication for autonomous publishing agents. mindX agents present an Ethereum wallet signature over a one-time challenge; the plugin returns a short-lived JWT good for the WordPress REST API. No passwords on the wire. No Application Passwords to rotate. Authorization is gated by an admin-curated allowlist of wallet addresses.
 * Version:           0.1.0
 * Requires at least: 5.6
 * Requires PHP:      7.4
 * Author:            mindX
 * Author URI:        https://mindx.pythai.net
 * License:           Apache-2.0
 * License URI:       https://www.apache.org/licenses/LICENSE-2.0
 * Text Domain:       mindx-publish-auth
 *
 * (c) 2026 AgenticPlace / mindX contributors. Apache-2.0.
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit; // No direct access.
}

define( 'MINDX_AUTH_VERSION', '0.1.0' );
define( 'MINDX_AUTH_PLUGIN_FILE', __FILE__ );
define( 'MINDX_AUTH_PLUGIN_DIR', plugin_dir_path( __FILE__ ) );

// JWT defaults — overridable via filters below.
define( 'MINDX_AUTH_JWT_TTL_DEFAULT',        30 * MINUTE_IN_SECONDS );
define( 'MINDX_AUTH_CHALLENGE_TTL_DEFAULT',   5 * MINUTE_IN_SECONDS );
define( 'MINDX_AUTH_AUDIT_LOG_MAX',          50 );

// Option keys (single prefix, easy to grep / clean up).
define( 'MINDX_AUTH_OPT_SECRET',       'mindx_auth_jwt_secret' );        // HS256 key, rotated
define( 'MINDX_AUTH_OPT_ALLOWLIST',    'mindx_auth_allowlist' );          // address => wp_user_id map
define( 'MINDX_AUTH_OPT_AUDIT',        'mindx_auth_audit_log' );          // ring buffer of auth events
define( 'MINDX_AUTH_OPT_JWT_TTL',      'mindx_auth_jwt_ttl' );            // override default JWT TTL
define( 'MINDX_AUTH_OPT_CHAL_TTL',     'mindx_auth_challenge_ttl' );      // override challenge TTL

// ─── Includes ─────────────────────────────────────────────────────
require_once MINDX_AUTH_PLUGIN_DIR . 'includes/keccak.php';
require_once MINDX_AUTH_PLUGIN_DIR . 'includes/secp256k1.php';
require_once MINDX_AUTH_PLUGIN_DIR . 'includes/class-mindx-auth-jwt.php';
require_once MINDX_AUTH_PLUGIN_DIR . 'includes/class-mindx-auth-rest.php';
require_once MINDX_AUTH_PLUGIN_DIR . 'includes/class-mindx-auth-settings.php';

// ─── Activation: generate the per-site JWT secret on first install ──
register_activation_hook( __FILE__, function () {
    // Generate a 32-byte HS256 secret iff none exists. Idempotent — reactivation
    // does NOT rotate the secret (operator does that explicitly via settings).
    if ( ! get_option( MINDX_AUTH_OPT_SECRET ) ) {
        update_option(
            MINDX_AUTH_OPT_SECRET,
            bin2hex( random_bytes( 32 ) ),
            false  // do not autoload — only loaded when auth fires
        );
    }
    if ( get_option( MINDX_AUTH_OPT_ALLOWLIST, null ) === null ) {
        // Empty allowlist by default — operator must add wordpress.agent's address.
        update_option( MINDX_AUTH_OPT_ALLOWLIST, array(), false );
    }
    if ( get_option( MINDX_AUTH_OPT_AUDIT, null ) === null ) {
        update_option( MINDX_AUTH_OPT_AUDIT, array(), false );
    }
} );

// ─── Deactivation: leave data in place ──────────────────────────────
register_deactivation_hook( __FILE__, function () {
    // Deliberately do NOT delete the secret / allowlist on deactivation —
    // the operator may toggle the plugin off-and-on without losing config.
    // Use the "Uninstall" action (delete-plugin) for a full cleanup; see uninstall.php.
} );

// ─── Bootstrap classes ─────────────────────────────────────────────
add_action( 'plugins_loaded', function () {
    MindX_Auth_REST::register();
    MindX_Auth_Settings::register();
} );

// ─── Convenience helpers exposed for other plugins / themes ─────────

/**
 * Return the current allowlist as an associative map of
 * `lowercased_address => wp_user_id`.
 */
function mindx_auth_get_allowlist() {
    $raw = get_option( MINDX_AUTH_OPT_ALLOWLIST, array() );
    if ( ! is_array( $raw ) ) {
        return array();
    }
    $out = array();
    foreach ( $raw as $addr => $uid ) {
        $out[ strtolower( (string) $addr ) ] = (int) $uid;
    }
    return $out;
}

/**
 * Append an event to the audit log (ring buffer of last MINDX_AUTH_AUDIT_LOG_MAX entries).
 * Never raises.
 */
function mindx_auth_record_event( $kind, $data = array() ) {
    $log = get_option( MINDX_AUTH_OPT_AUDIT, array() );
    if ( ! is_array( $log ) ) {
        $log = array();
    }
    $log[] = array(
        'at'   => time(),
        'kind' => (string) $kind,
        'ip'   => isset( $_SERVER['REMOTE_ADDR'] ) ? wp_unslash( $_SERVER['REMOTE_ADDR'] ) : '',
        'data' => $data,
    );
    if ( count( $log ) > MINDX_AUTH_AUDIT_LOG_MAX ) {
        $log = array_slice( $log, -MINDX_AUTH_AUDIT_LOG_MAX );
    }
    update_option( MINDX_AUTH_OPT_AUDIT, $log, false );
}
