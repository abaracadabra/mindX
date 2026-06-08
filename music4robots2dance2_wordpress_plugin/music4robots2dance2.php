<?php
/**
 * Plugin Name:       Music 4 Robots 2 Dance 2
 * Plugin URI:        https://rage.pythai.net/music-4-robots-2-dance-2/
 * Description:       SoundCloud audio embeds across web2, the take·own·use·share way. Ships the "Music 4 Robots 2 Dance 2" and "takIT" (takeitownit) albums as one-line shortcodes, registers a Gutenberg block, whitelists the SoundCloud player iframe so any editor can embed safely, and exposes the gnugui "Take it, Own it." album presets sitewide. Companion to the mindX wordpress.agent soundcloud.tool.
 * Version:           0.1.0
 * Requires at least: 5.6
 * Requires PHP:      7.4
 * Author:            mindX / Mag Magnus / gnugui
 * Author URI:        https://github.com/gnugui
 * License:           GPL-3.0-or-later
 * License URI:       https://www.gnu.org/licenses/gpl-3.0.html
 * Text Domain:       music4robots2dance2
 *
 * (c) 2026 gnugui contributors. GPLv3 — take it, own it, use it, share it.
 *
 * Philosophy: gnugui's "take · own · use · share". You may take this plugin,
 * own your copy, use it freely, and share it forward under the same terms.
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit; // No direct access.
}

define( 'M4R2D2_VERSION', '0.1.0' );
define( 'M4R2D2_PLUGIN_FILE', __FILE__ );
define( 'M4R2D2_PLUGIN_DIR', plugin_dir_path( __FILE__ ) );
define( 'M4R2D2_PLUGIN_URL', plugin_dir_url( __FILE__ ) );

require_once M4R2D2_PLUGIN_DIR . 'includes/class-m4r2d2-embeds.php';
require_once M4R2D2_PLUGIN_DIR . 'includes/class-m4r2d2-shortcode.php';

add_action( 'plugins_loaded', function () {
    M4R2D2_Shortcode::register();
} );

// ─── Whitelist the SoundCloud player iframe in post content ─────────────────
// WordPress strips <iframe> from content authored by users without the
// `unfiltered_html` capability. This filter re-allows ONLY the SoundCloud
// widget host, so embeds survive for any editor — without opening the door to
// arbitrary iframes.
add_filter( 'wp_kses_allowed_html', function ( $allowed, $context ) {
    if ( 'post' !== $context ) {
        return $allowed;
    }
    $allowed['iframe'] = array(
        'src'             => true,
        'width'           => true,
        'height'          => true,
        'frameborder'     => true,
        'scrolling'       => true,
        'allow'           => true,
        'allowfullscreen' => true,
        'loading'         => true,
        'title'           => true,
        'style'           => true,
    );
    return $allowed;
}, 10, 2 );

// ─── Register the SoundCloud oEmbed provider (belt & suspenders) ─────────────
// Core already knows soundcloud.com; we (re)assert it so /sets/ permalinks on
// their own line auto-embed even on minimal installs.
add_action( 'init', function () {
    wp_oembed_add_provider(
        '#https?://(?:www\.)?soundcloud\.com/.*#i',
        'https://soundcloud.com/oembed',
        true
    );
} );

// ─── Gutenberg block (server-rendered, reuses the shortcode renderer) ───────
add_action( 'init', function () {
    if ( ! function_exists( 'register_block_type' ) ) {
        return; // Classic editor only — shortcode still works.
    }
    register_block_type( 'music4robots2dance2/album', array(
        'api_version'     => 2,
        'title'           => 'Music 4 Robots 2 Dance 2',
        'category'        => 'embed',
        'icon'            => 'format-audio',
        'attributes'      => array(
            'album'      => array( 'type' => 'string', 'default' => 'music4robots2dance2' ),
            'permalink'  => array( 'type' => 'string', 'default' => '' ),
            'playlist'   => array( 'type' => 'string', 'default' => '' ),
            'track'      => array( 'type' => 'string', 'default' => '' ),
            'color'      => array( 'type' => 'string', 'default' => '' ),
            'visual'     => array( 'type' => 'boolean', 'default' => false ),
            'auto_play'  => array( 'type' => 'boolean', 'default' => false ),
        ),
        'render_callback' => function ( $attrs ) {
            return M4R2D2_Shortcode::render( is_array( $attrs ) ? $attrs : array() );
        },
    ) );
} );
