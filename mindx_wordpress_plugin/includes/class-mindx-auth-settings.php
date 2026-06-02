<?php
/**
 * Admin settings page + the Bearer-JWT → WP-user authentication filter
 * for mindX Publish Auth.
 *
 * Settings page: Settings → mindX Publish Auth
 *   - Allowlist editor: paste lines of "0x<address> <wp_user_login>"
 *   - "Rotate JWT secret" button (renders an admin-notice with the date
 *     of rotation; the secret itself never appears in the UI)
 *   - Last 50 auth events (success + failure, with addresses & error codes)
 *   - JWT + challenge TTL knobs
 *
 * REST filter: every /wp-json/* request is checked. If the request
 * carries `Authorization: Bearer <jwt>` AND the JWT verifies under the
 * configured secret AND the `sub` claim resolves to a real WP user, we
 * log that user in for the lifetime of the request. Other auth methods
 * (cookies, Application Passwords) still work — we just add a new one.
 *
 * (c) 2026 AgenticPlace / mindX contributors. Apache-2.0.
 */

if ( ! defined( 'ABSPATH' ) ) { exit; }

if ( ! class_exists( 'MindX_Auth_Settings' ) ) :

class MindX_Auth_Settings {

    const SLUG = 'mindx-publish-auth';

    public static function register() {
        add_action( 'admin_menu',            array( __CLASS__, 'add_menu' ) );
        add_action( 'admin_init',            array( __CLASS__, 'handle_post' ) );
        add_filter( 'determine_current_user', array( __CLASS__, 'authenticate_bearer' ), 20 );
        add_filter( 'rest_authentication_errors', array( __CLASS__, 'rest_auth_pass_through' ), 99 );
    }

    // ─── Admin menu + page ────────────────────────────────────────

    public static function add_menu() {
        add_options_page(
            'mindX Publish Auth',
            'mindX Publish Auth',
            'manage_options',
            self::SLUG,
            array( __CLASS__, 'render_page' )
        );
    }

    public static function render_page() {
        if ( ! current_user_can( 'manage_options' ) ) return;

        $allowlist = mindx_auth_get_allowlist();
        $allowlist_text = '';
        foreach ( $allowlist as $addr => $uid ) {
            $user = get_userdata( $uid );
            $login = $user ? $user->user_login : "(missing-user-{$uid})";
            $allowlist_text .= $addr . ' ' . $login . "\n";
        }

        $chal_ttl = (int) get_option( MINDX_AUTH_OPT_CHAL_TTL, MINDX_AUTH_CHALLENGE_TTL_DEFAULT );
        $jwt_ttl  = (int) get_option( MINDX_AUTH_OPT_JWT_TTL,  MINDX_AUTH_JWT_TTL_DEFAULT );
        $audit    = get_option( MINDX_AUTH_OPT_AUDIT, array() );
        if ( ! is_array( $audit ) ) $audit = array();

        ?>
        <div class="wrap">
            <h1>mindX Publish Auth</h1>
            <p>Lets autonomous mindX agents publish to this WordPress install by signing a one-time challenge with their wallet — no passwords on the wire. Add the wallet address(es) to the allowlist below, link each to a WP user, and the rest is automatic.</p>

            <?php settings_errors( 'mindx_auth' ); ?>

            <form method="post" action="">
                <?php wp_nonce_field( 'mindx_auth_settings', 'mindx_auth_nonce' ); ?>

                <h2>Allowlist</h2>
                <p>One entry per line: <code>0x&lt;wallet-address&gt; &lt;wp-user-login&gt;</code>. Whitespace separates the two columns. Comments start with <code>#</code>.</p>
                <textarea name="mindx_auth_allowlist" rows="6" cols="100" style="font-family:monospace;"><?php echo esc_textarea( $allowlist_text ); ?></textarea>

                <h2>Token lifetimes</h2>
                <table class="form-table">
                    <tr>
                        <th><label for="mindx_auth_chal_ttl">Challenge TTL (seconds)</label></th>
                        <td><input type="number" name="mindx_auth_chal_ttl" id="mindx_auth_chal_ttl" min="30" max="3600" value="<?php echo (int) $chal_ttl; ?>" /> &nbsp; default 300 (5 min)</td>
                    </tr>
                    <tr>
                        <th><label for="mindx_auth_jwt_ttl">JWT TTL (seconds)</label></th>
                        <td><input type="number" name="mindx_auth_jwt_ttl" id="mindx_auth_jwt_ttl" min="60" max="86400" value="<?php echo (int) $jwt_ttl; ?>" /> &nbsp; default 1800 (30 min)</td>
                    </tr>
                </table>

                <p><?php submit_button( 'Save', 'primary', 'mindx_auth_save', false ); ?>
                   &nbsp;
                   <button type="submit" name="mindx_auth_rotate" value="1" class="button button-secondary" onclick="return confirm('Rotate the JWT secret? All existing tokens will be invalidated immediately.');">
                       Rotate JWT secret
                   </button>
                </p>
            </form>

            <h2>Recent auth events (last <?php echo count( $audit ); ?>)</h2>
            <?php if ( empty( $audit ) ): ?>
                <p><em>None yet.</em></p>
            <?php else: ?>
                <table class="widefat striped" style="font-family:monospace; font-size:0.9em;">
                    <thead><tr><th>When</th><th>Kind</th><th>IP</th><th>Data</th></tr></thead>
                    <tbody>
                    <?php foreach ( array_reverse( $audit ) as $ev ): ?>
                        <tr>
                            <td><?php echo esc_html( gmdate( 'Y-m-d H:i:s', (int) ( $ev['at'] ?? 0 ) ) ); ?></td>
                            <td><?php echo esc_html( $ev['kind'] ?? '?' ); ?></td>
                            <td><?php echo esc_html( $ev['ip'] ?? '' ); ?></td>
                            <td><?php echo esc_html( wp_json_encode( $ev['data'] ?? array() ) ); ?></td>
                        </tr>
                    <?php endforeach; ?>
                    </tbody>
                </table>
            <?php endif; ?>

            <h2>Diagnostics</h2>
            <p>The unauthenticated diagnostic endpoint reports whether the cryptographic substrate is loaded on this host:
                <br>
                <code>curl <?php echo esc_html( home_url( '/wp-json/mindx/v1/auth/diagnose' ) ); ?></code>
            </p>
            <p>If <code>gmp_loaded</code> is false, signature verification will not work — install the PHP <code>gmp</code> extension (most shared hosts have it; ask Hostinger support if not).</p>
        </div>
        <?php
    }

    // ─── Form POST handler ─────────────────────────────────────────

    public static function handle_post() {
        if ( ! isset( $_POST['mindx_auth_nonce'] ) ) return;
        if ( ! current_user_can( 'manage_options' ) ) return;
        check_admin_referer( 'mindx_auth_settings', 'mindx_auth_nonce' );

        if ( isset( $_POST['mindx_auth_rotate'] ) ) {
            MindX_Auth_JWT::rotate_secret();
            mindx_auth_record_event( 'jwt_secret_rotated', array( 'by_user' => get_current_user_id() ) );
            add_settings_error( 'mindx_auth', 'rotated', 'JWT secret rotated. All previously-issued tokens are now invalid.', 'updated' );
            return;
        }

        if ( isset( $_POST['mindx_auth_save'] ) ) {
            // Parse the allowlist textarea.
            $raw = isset( $_POST['mindx_auth_allowlist'] ) ? wp_unslash( $_POST['mindx_auth_allowlist'] ) : '';
            $new_allow = array();
            $rejected  = array();
            foreach ( preg_split( '/\r\n|\r|\n/', (string) $raw ) as $line ) {
                $line = trim( $line );
                if ( $line === '' || $line[0] === '#' ) continue;
                $parts = preg_split( '/\s+/', $line, 2 );
                if ( count( $parts ) !== 2 ) {
                    $rejected[] = $line . '  (expected "address login")';
                    continue;
                }
                list( $addr_raw, $login ) = $parts;
                $addr = strtolower( $addr_raw );
                if ( ! preg_match( '/^0x[0-9a-f]{40}$/', $addr ) ) {
                    $rejected[] = $line . '  (address must be 0x + 40 hex)';
                    continue;
                }
                $user = get_user_by( 'login', $login );
                if ( ! $user ) {
                    $rejected[] = $line . '  (no WP user with login "' . esc_html( $login ) . '")';
                    continue;
                }
                $new_allow[ $addr ] = (int) $user->ID;
            }
            update_option( MINDX_AUTH_OPT_ALLOWLIST, $new_allow, false );

            $chal = max( 30, min( 3600, (int) ( $_POST['mindx_auth_chal_ttl'] ?? MINDX_AUTH_CHALLENGE_TTL_DEFAULT ) ) );
            $jwt  = max( 60, min( 86400, (int) ( $_POST['mindx_auth_jwt_ttl']  ?? MINDX_AUTH_JWT_TTL_DEFAULT ) ) );
            update_option( MINDX_AUTH_OPT_CHAL_TTL, $chal, false );
            update_option( MINDX_AUTH_OPT_JWT_TTL,  $jwt,  false );

            add_settings_error(
                'mindx_auth',
                'saved',
                sprintf( 'Saved. Allowlist: %d entries.', count( $new_allow ) ) .
                ( $rejected ? '  Rejected lines:<br><code>' . esc_html( implode( "\n", $rejected ) ) . '</code>' : '' ),
                'updated'
            );
            mindx_auth_record_event( 'settings_saved', array(
                'allowlist_count' => count( $new_allow ),
                'rejected_count'  => count( $rejected ),
            ) );
        }
    }

    // ─── Bearer JWT → WP user filter ──────────────────────────────

    /**
     * If the request carries a valid mindX-issued JWT, return the
     * corresponding WP user id. WordPress core then treats the request as
     * authenticated under that user for the rest of the lifecycle.
     */
    public static function authenticate_bearer( $user_id ) {
        if ( ! empty( $user_id ) ) return $user_id;  // already authenticated some other way

        $auth = self::extract_bearer_header();
        if ( ! $auth ) return $user_id;

        $verified = MindX_Auth_JWT::verify( $auth );
        if ( is_wp_error( $verified ) ) {
            // Don't surface the verification error here — REST core will
            // either accept another auth method or return 401. We just
            // record it for the audit log.
            mindx_auth_record_event( 'bearer_reject', array(
                'code' => $verified->get_error_code(),
            ) );
            return $user_id;
        }
        $u = get_userdata( (int) $verified['sub'] );
        if ( ! $u ) {
            mindx_auth_record_event( 'bearer_user_missing', array( 'sub' => $verified['sub'] ) );
            return $user_id;
        }
        // Success — return the user id so core treats this as logged in.
        return (int) $u->ID;
    }

    /** Don't surface our Bearer presence as a *blocking* error if it fails — let
     * other auth layers try. */
    public static function rest_auth_pass_through( $err ) {
        return $err;
    }

    private static function extract_bearer_header() {
        $hdr = '';
        if ( function_exists( 'apache_request_headers' ) ) {
            $h = apache_request_headers();
            if ( isset( $h['Authorization'] ) )  $hdr = $h['Authorization'];
            if ( isset( $h['authorization'] ) )  $hdr = $h['authorization'];
        }
        if ( ! $hdr && isset( $_SERVER['HTTP_AUTHORIZATION'] ) ) $hdr = $_SERVER['HTTP_AUTHORIZATION'];
        if ( ! $hdr && isset( $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ) ) $hdr = $_SERVER['REDIRECT_HTTP_AUTHORIZATION'];
        if ( ! $hdr ) return '';

        if ( stripos( $hdr, 'Bearer ' ) !== 0 ) return '';
        return trim( substr( $hdr, 7 ) );
    }
}

endif;
