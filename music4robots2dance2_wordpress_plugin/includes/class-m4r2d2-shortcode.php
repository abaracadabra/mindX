<?php
/**
 * Shortcodes for SoundCloud audio embeds (pro player).
 *
 *   [m4r2d2]                                  → the highlights: Music 4 Robots 2
 *                                               Dance 2, custom controls + the
 *                                               story link to the rage article.
 *   [m4r2d2 album="takit"]                    → the takIT (takeitownit) album
 *   [m4r2d2 playlist="2249417369" color="9d7833"]
 *   [m4r2d2 track="123456789" mode="compact"]
 *   [m4r2d2 url="https://soundcloud.com/mag-magnus/sets/takit-1"]
 *   [m4r2d2 theme="light" controls="false" sticky="true" lazy="true"]
 *   [soundcloud ...]                          → alias of [m4r2d2]
 *   [m4r2d2_drop]                             → a "drop": lazy + sticky dock,
 *                                               permission-gated (play = consent).
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
        add_shortcode( 'm4r2d2_drop', array( __CLASS__, 'render_drop' ) );
    }

    private static function truthy( $v ) {
        return in_array( strtolower( (string) $v ), array( '1', 'true', 'yes', 'on' ), true );
    }

    /** Normalize shortcode atts → the array M4R2D2_Embeds::player_html() expects. */
    private static function opts( $atts, $defaults = array() ) {
        $a = shortcode_atts( array_merge( array(
            'album'       => '',
            'url'         => '',
            'permalink'   => '',
            'playlist'    => '',
            'track'       => '',
            'color'       => '',
            'height'      => '',
            'mode'        => '',     // playlist|visual|compact
            'theme'       => 'dark',
            'visual'      => '',
            'controls'    => 'true',
            'sticky'      => 'false',
            'lazy'        => 'false',
            'autoplay'    => 'false',
            'story'       => null,   // null → default highlights link; "" suppresses
            'story_label' => '',
            'title'       => '',
            'artist'      => '',
        ), $defaults ), is_array( $atts ) ? $atts : array(), 'm4r2d2' );

        // mode sugar
        if ( $a['mode'] === 'visual' && $a['visual'] === '' ) { $a['visual'] = 'true'; }
        if ( $a['mode'] === 'compact' && $a['height'] === '' ) { $a['height'] = (string) M4R2D2_Embeds::HEIGHT_TRACK; }

        $o = array(
            'album'    => $a['album'],
            'url'      => $a['url'] !== '' ? $a['url'] : $a['permalink'],
            'playlist' => $a['playlist'],
            'track'    => $a['track'],
            'color'    => $a['color'],
            'height'   => $a['height'],
            'theme'    => $a['theme'],
            'visual'   => $a['visual'] !== '' ? self::truthy( $a['visual'] ) : null,
            'controls' => self::truthy( $a['controls'] ),
            'sticky'   => self::truthy( $a['sticky'] ),
            'lazy'     => self::truthy( $a['lazy'] ),
            'autoplay' => self::truthy( $a['autoplay'] ),
            'title'    => $a['title'],
            'artist'   => $a['artist'],
            'story_label' => $a['story_label'],
        );
        if ( $a['story'] !== null ) { $o['story'] = $a['story']; } // honor explicit (incl. "")
        if ( $o['visual'] === null ) { unset( $o['visual'] ); }
        return $o;
    }

    public static function render( $atts ) {
        if ( class_exists( 'Music4Robots2Dance2' ) ) { Music4Robots2Dance2::need_assets(); }
        $html = M4R2D2_Embeds::player_html( self::opts( $atts ) );
        return $html === '' ? '' : $html;
    }

    /** A "drop": permission-gated (lazy facade = consent), docks while playing. */
    public static function render_drop( $atts ) {
        if ( class_exists( 'Music4Robots2Dance2' ) ) { Music4Robots2Dance2::need_assets(); }
        return M4R2D2_Embeds::player_html( self::opts( $atts, array(
            'lazy' => 'true', 'sticky' => 'true', 'controls' => 'true',
        ) ) );
    }
}
