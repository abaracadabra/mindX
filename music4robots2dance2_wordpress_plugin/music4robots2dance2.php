<?php
/**
 * Plugin Name:       Music 4 Robots 2 Dance 2
 * Plugin URI:        https://rage.pythai.net/take-it-own-it-codephreak/
 * Description:       Pro SoundCloud player for web2, the take·own·use·share way. One shortcode [m4r2d2] drops a custom-control player (play/pause/seek/volume, lazy facade, sticky dock) for the "Music 4 Robots 2 Dance 2" + "takIT" (takeitownit) albums, links the story on rage.pythai.net, and ships a paste-anywhere DROP. v1 alpha working example. Separate from — and complementary to — the mindX Publish Auth plugin.
 * Version:           1.0.0-alpha
 * Requires at least: 5.6
 * Requires PHP:      7.4
 * Author:            mindX / Mag Magnus / gnugui
 * Author URI:        https://github.com/gnugui
 * License:           GPL-3.0-or-later
 * License URI:       https://www.gnu.org/licenses/gpl-3.0.html
 * Text Domain:       music4robots2dance2
 *
 * (c) 2026 gnugui contributors. GPLv3 — take it, own it, use it, share it.
 * Songs owned by Professor Codephreak under the gnugui take·own·use·share
 * promotional licence (GPLv3-derived). The story: https://rage.pythai.net/take-it-own-it-codephreak/
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit; // No direct access.
}

define( 'M4R2D2_VERSION', '1.0.0-alpha' );
define( 'M4R2D2_PLUGIN_FILE', __FILE__ );
define( 'M4R2D2_PLUGIN_DIR', plugin_dir_path( __FILE__ ) );
define( 'M4R2D2_PLUGIN_URL', plugin_dir_url( __FILE__ ) );
// Sitewide auto-drop option — DEFAULT YES (a player installs itself, gated by the
// play-to-consent facade). Operators can turn it off in Settings → Music 4 Robots.
define( 'M4R2D2_OPT_AUTODROP', 'm4r2d2_autodrop' );

require_once M4R2D2_PLUGIN_DIR . 'includes/class-m4r2d2-embeds.php';
require_once M4R2D2_PLUGIN_DIR . 'includes/class-m4r2d2-shortcode.php';

final class Music4Robots2Dance2 {

    private static $need_assets = false;

    public static function boot() {
        M4R2D2_Shortcode::register();
        add_action( 'wp_enqueue_scripts', array( __CLASS__, 'register_assets' ) );
        add_action( 'wp_footer', array( __CLASS__, 'maybe_autodrop' ), 20 );
        add_action( 'init', array( __CLASS__, 'register_block' ) );
        add_action( 'init', array( __CLASS__, 'register_oembed' ) );
        add_filter( 'wp_kses_allowed_html', array( __CLASS__, 'allow_iframe' ), 10, 2 );
    }

    /** Register (don't enqueue) the player assets so shortcodes can pull them on demand. */
    public static function register_assets() {
        wp_register_style( 'm4r2d2-player', M4R2D2_PLUGIN_URL . 'assets/m4r2d2-player.css', array(), M4R2D2_VERSION );
        wp_register_script( 'm4r2d2-player', M4R2D2_PLUGIN_URL . 'assets/m4r2d2-player.js', array(), M4R2D2_VERSION, true );
        if ( self::$need_assets ) {
            self::need_assets();
        }
    }

    /** Called by the shortcode renderer; enqueues the player assets exactly once. */
    public static function need_assets() {
        self::$need_assets = true;
        if ( wp_script_is( 'm4r2d2-player', 'registered' ) ) {
            wp_enqueue_style( 'm4r2d2-player' );
            wp_enqueue_script( 'm4r2d2-player' );
        }
    }

    /**
     * Sitewide DROP — default YES. Injects one permission-gated highlights player
     * on the front end via the m4r2d2:drop injective event, unless the operator
     * disabled it or a shortcode already placed a player on the page.
     */
    public static function maybe_autodrop() {
        if ( is_admin() || is_feed() ) {
            return;
        }
        $enabled = get_option( M4R2D2_OPT_AUTODROP, '1' );
        /** Filter: return false to disable the sitewide auto-drop. */
        $enabled = apply_filters( 'm4r2d2_autodrop_enabled', $enabled !== '0' && $enabled !== false );
        if ( ! $enabled || self::$need_assets ) {
            return; // off, or a real player is already on the page
        }
        wp_enqueue_style( 'm4r2d2-player' );
        wp_enqueue_script( 'm4r2d2-player' );
        // Fire the injective event once the core is ready.
        $story = esc_js( M4R2D2_Embeds::ARTICLE_URL );
        $album = esc_js( M4R2D2_Embeds::DEFAULT_ALBUM );
        echo "\n<script>(function(){function d(){window.M4R2D2&&window.M4R2D2.drop({album:'{$album}',sticky:true,permission:'ask',story:'{$story}'});}"
            . "if(window.M4R2D2)d();else window.addEventListener('m4r2d2:ready',d,{once:true});"
            . "window.addEventListener('load',function(){if(window.M4R2D2)d();});})();</script>\n";
    }

    public static function register_block() {
        if ( ! function_exists( 'register_block_type' ) ) {
            return;
        }
        register_block_type( 'music4robots2dance2/album', array(
            'api_version'     => 2,
            'title'           => 'Music 4 Robots 2 Dance 2',
            'category'        => 'embed',
            'icon'            => 'format-audio',
            'attributes'      => array(
                'album'     => array( 'type' => 'string', 'default' => 'music4robots2dance2' ),
                'url'       => array( 'type' => 'string', 'default' => '' ),
                'playlist'  => array( 'type' => 'string', 'default' => '' ),
                'track'     => array( 'type' => 'string', 'default' => '' ),
                'theme'     => array( 'type' => 'string', 'default' => 'dark' ),
                'color'     => array( 'type' => 'string', 'default' => '' ),
                'controls'  => array( 'type' => 'boolean', 'default' => true ),
                'sticky'    => array( 'type' => 'boolean', 'default' => false ),
                'lazy'      => array( 'type' => 'boolean', 'default' => false ),
                'visual'    => array( 'type' => 'boolean', 'default' => false ),
            ),
            'render_callback' => function ( $attrs ) {
                self::need_assets();
                return M4R2D2_Shortcode::render( is_array( $attrs ) ? $attrs : array() );
            },
        ) );
    }

    public static function register_oembed() {
        wp_oembed_add_provider( '#https?://(?:www\.)?soundcloud\.com/.*#i', 'https://soundcloud.com/oembed', true );
    }

    /** Re-allow ONLY the SoundCloud player iframe in post content (not arbitrary iframes). */
    public static function allow_iframe( $allowed, $context ) {
        if ( 'post' !== $context ) {
            return $allowed;
        }
        $allowed['iframe'] = array(
            'src' => true, 'width' => true, 'height' => true, 'frameborder' => true,
            'scrolling' => true, 'allow' => true, 'allowfullscreen' => true,
            'loading' => true, 'title' => true, 'style' => true, 'class' => true,
        );
        return $allowed;
    }
}

add_action( 'plugins_loaded', array( 'Music4Robots2Dance2', 'boot' ) );
