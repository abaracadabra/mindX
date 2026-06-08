<?php
/**
 * Shortcodes for SoundCloud audio embeds.
 *
 *   [m4r2d2]                                  → the Music 4 Robots 2 Dance 2 album
 *   [m4r2d2 album="takit"]                    → the takIT (takeitownit) album
 *   [m4r2d2 playlist="2249417369" color="9d7833"]
 *   [m4r2d2 track="123456789" visual="true"]
 *   [m4r2d2 url="https://soundcloud.com/mag-magnus/sets/takit-1"]
 *   [soundcloud ...]                          → alias of [m4r2d2]
 *
 * @package music4robots2dance2
 * License: GPL-3.0-or-later
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class M4R2D2_Shortcode {

    public static function register() {
        add_shortcode( 'm4r2d2', array( __CLASS__, 'render' ) );
        add_shortcode( 'soundcloud', array( __CLASS__, 'render' ) );
    }

    /**
     * Render an embed from shortcode/block attributes. Precedence:
     * url → playlist → track → album (default: music4robots2dance2).
     */
    public static function render( $atts ) {
        $a = shortcode_atts( array(
            'album'     => '',
            'url'       => '',
            'permalink' => '',
            'playlist'  => '',
            'track'     => '',
            'color'     => '',
            'height'    => '',
            'visual'    => '',
            'auto_play' => '',
        ), is_array( $atts ) ? $atts : array(), 'm4r2d2' );

        $truthy = function ( $v ) {
            return in_array( strtolower( (string) $v ), array( '1', 'true', 'yes', 'on' ), true );
        };

        $opts = array();
        if ( '' !== $a['color'] )  { $opts['color']  = $a['color']; }
        if ( '' !== $a['height'] ) { $opts['height'] = (int) $a['height']; }
        if ( '' !== $a['visual'] ) { $opts['visual'] = $truthy( $a['visual'] ); }
        if ( '' !== $a['auto_play'] ) { $opts['auto_play'] = $truthy( $a['auto_play'] ); }

        $permalink = '' !== $a['url'] ? $a['url'] : $a['permalink'];

        $html = '';
        if ( '' !== $permalink ) {
            $is_set = ( false !== strpos( $permalink, '/sets/' ) );
            if ( ! isset( $opts['height'] ) ) {
                $opts['height'] = $is_set ? M4R2D2_Embeds::HEIGHT_PLAYLIST : M4R2D2_Embeds::HEIGHT_TRACK;
            }
            $html = M4R2D2_Embeds::embed( $permalink, $opts );
        } elseif ( '' !== $a['playlist'] ) {
            $html = M4R2D2_Embeds::embed( M4R2D2_Embeds::playlist_resource_url( $a['playlist'] ), $opts );
        } elseif ( '' !== $a['track'] ) {
            if ( ! isset( $opts['height'] ) ) {
                $opts['height'] = M4R2D2_Embeds::HEIGHT_TRACK;
            }
            $html = M4R2D2_Embeds::embed( M4R2D2_Embeds::track_resource_url( $a['track'] ), $opts );
        } else {
            $key  = '' !== $a['album'] ? $a['album'] : 'music4robots2dance2';
            $html = M4R2D2_Embeds::album_embed( $key, $opts );
        }

        if ( '' === $html ) {
            return '';
        }
        return '<div class="m4r2d2-embed">' . $html . '</div>';
    }
}
