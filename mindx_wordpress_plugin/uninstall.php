<?php
/**
 * Uninstall handler for mindX Publish Auth. Fires when the operator
 * clicks "Delete" on the plugin in the WP admin (NOT on deactivate).
 *
 * Removes every option this plugin owns. Does NOT touch user accounts
 * or user_meta — those belong to WordPress, not the plugin.
 *
 * (c) 2026 AgenticPlace / mindX contributors. Apache-2.0.
 */

if ( ! defined( 'WP_UNINSTALL_PLUGIN' ) ) {
    exit;
}

foreach ( array(
    'mindx_auth_jwt_secret',
    'mindx_auth_allowlist',
    'mindx_auth_audit_log',
    'mindx_auth_jwt_ttl',
    'mindx_auth_challenge_ttl',
) as $opt ) {
    delete_option( $opt );
}

// Clear any outstanding challenge transients.
global $wpdb;
$wpdb->query(
    $wpdb->prepare(
        "DELETE FROM {$wpdb->options} WHERE option_name LIKE %s OR option_name LIKE %s",
        '_transient_mindx_auth_chal_%',
        '_transient_timeout_mindx_auth_chal_%'
    )
);
