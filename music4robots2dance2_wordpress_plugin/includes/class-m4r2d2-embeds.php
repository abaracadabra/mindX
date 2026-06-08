<?php
/**
 * SoundCloud embed builder — PHP mirror of the mindX wordpress.agent
 * soundcloud.tool (agents/wordpress_agent/soundcloud.py). Pure functions:
 * resource URL → player URL → iframe + attribution HTML. Deterministic.
 *
 * @package music4robots2dance2
 * License: GPL-3.0-or-later
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class M4R2D2_Embeds {

    const PLAYER_BASE   = 'https://w.soundcloud.com/player/';
    const COLOR_DEFAULT = 'ff5500';
    const HEIGHT_TRACK    = 166;
    const HEIGHT_VISUAL   = 300;
    const HEIGHT_PLAYLIST = 450;

    /**
     * Known albums — the Professor Codephreak / Mag Magnus tribute set.
     * Keys mirror soundcloud.py KNOWN_PLAYLISTS exactly.
     */
    public static function albums() {
        return array(
            'takit' => array(
                'playlist_id' => '2249417369',
                'title'       => 'takIT',
                'set_url'     => 'https://soundcloud.com/mag-magnus/sets/takit-1',
                'color'       => '9d7833',
                'height'      => self::HEIGHT_PLAYLIST,
                'visual'      => false,
                'blurb'       => 'home of "takeitownit" — Take it, Own it. (use it · share it) — inspired by github.com/gnugui',
            ),
            'music4robots2dance2' => array(
                'playlist_id' => '2216206346',
                'title'       => 'Music  4 Robots 2 Dance 2',
                'set_url'     => 'https://soundcloud.com/mag-magnus/sets/music-for-robots-to-dance-2',
                'color'       => 'ff5500',
                'height'      => self::HEIGHT_VISUAL,
                'visual'      => true,
                'blurb'       => 'the album robots dance to',
            ),
        );
    }

    const ARTIST_NAME = 'Mag Magnus';
    const ARTIST_URL  = 'https://soundcloud.com/mag-magnus';

    private static function norm_color( $color ) {
        $c = ltrim( trim( (string) $color ), '#' );
        if ( 0 === stripos( $c, '%23' ) ) {
            $c = substr( $c, 3 );
        }
        return '' === $c ? self::COLOR_DEFAULT : $c;
    }

    public static function playlist_resource_url( $playlist_id, $use_urn = true ) {
        $pid  = trim( (string) $playlist_id );
        $tail = $use_urn ? "soundcloud:playlists:{$pid}" : $pid;
        return "https://api.soundcloud.com/playlists/{$tail}";
    }

    public static function track_resource_url( $track_id, $use_urn = true ) {
        $tid  = trim( (string) $track_id );
        $tail = $use_urn ? "soundcloud:tracks:{$tid}" : $tid;
        return "https://api.soundcloud.com/tracks/{$tail}";
    }

    /**
     * Build the w.soundcloud.com player URL. Single-encodes the resource URL
     * (path slashes kept, colons encoded) to match SoundCloud's own output.
     */
    public static function build_player_url( $resource_url, $opts = array() ) {
        $d = array(
            'color'         => self::COLOR_DEFAULT,
            'auto_play'     => false,
            'visual'        => false,
            'hide_related'  => false,
            'show_comments' => true,
            'show_user'     => true,
            'show_reposts'  => false,
            'show_teaser'   => true,
        );
        $o = array_merge( $d, $opts );
        $b = function ( $v ) { return $v ? 'true' : 'false'; };

        // rawurlencode then restore path slashes (safe="/" parity with python).
        $enc = str_replace( '%2F', '/', rawurlencode( $resource_url ) );

        $params  = 'url=' . $enc;
        $params .= '&color=%23' . self::norm_color( $o['color'] );
        $params .= '&auto_play=' . $b( $o['auto_play'] );
        $params .= '&hide_related=' . $b( $o['hide_related'] );
        $params .= '&show_comments=' . $b( $o['show_comments'] );
        $params .= '&show_user=' . $b( $o['show_user'] );
        $params .= '&show_reposts=' . $b( $o['show_reposts'] );
        $params .= '&show_teaser=' . $b( $o['show_teaser'] );
        if ( ! empty( $o['visual'] ) ) {
            $params .= '&visual=true';
        }
        return self::PLAYER_BASE . '?' . $params;
    }

    public static function attribution_html( $author_name, $author_url, $title = '', $title_url = '' ) {
        $style_wrap = 'font-size: 10px; color: #cccccc;line-break: anywhere;word-break: normal;'
            . 'overflow: hidden;white-space: nowrap;text-overflow: ellipsis; '
            . 'font-family: Interstate,Lucida Grande,Lucida Sans Unicode,Lucida Sans,'
            . 'Garuda,Verdana,Tahoma,sans-serif;font-weight: 100;';
        $style_a = 'color: #cccccc; text-decoration: none;';
        $parts   = array();
        $parts[] = sprintf(
            '<a href="%s" title="%s" target="_blank" style="%s">%s</a>',
            esc_url( $author_url ), esc_attr( $author_name ), esc_attr( $style_a ), esc_html( $author_name )
        );
        if ( '' !== $title ) {
            $href    = '' !== $title_url ? $title_url : $author_url;
            $parts[] = sprintf(
                '<a href="%s" title="%s" target="_blank" style="%s">%s</a>',
                esc_url( $href ), esc_attr( $title ), esc_attr( $style_a ), esc_html( $title )
            );
        }
        return sprintf( '<div style="%s">%s</div>', esc_attr( $style_wrap ), implode( ' · ', $parts ) );
    }

    /**
     * Full embed: player iframe + optional attribution div.
     */
    public static function embed( $resource_url, $opts = array() ) {
        $width  = isset( $opts['width'] ) ? $opts['width'] : '100%';
        $height = isset( $opts['height'] ) ? (int) $opts['height'] : self::HEIGHT_PLAYLIST;
        $src    = self::build_player_url( $resource_url, $opts );
        $iframe = sprintf(
            '<iframe width="%s" height="%d" scrolling="no" frameborder="no" '
            . 'allow="autoplay; encrypted-media" src="%s"></iframe>',
            esc_attr( $width ), $height, esc_url( $src )
        );
        if ( ! empty( $opts['attribution'] ) && is_array( $opts['attribution'] ) ) {
            $a       = $opts['attribution'];
            $iframe .= self::attribution_html(
                isset( $a['author_name'] ) ? $a['author_name'] : '',
                isset( $a['author_url'] ) ? $a['author_url'] : '',
                isset( $a['title'] ) ? $a['title'] : '',
                isset( $a['title_url'] ) ? $a['title_url'] : ''
            );
        }
        return $iframe;
    }

    public static function album_embed( $key, $opts = array() ) {
        $albums = self::albums();
        $k      = strtolower( trim( (string) $key ) );
        if ( ! isset( $albums[ $k ] ) ) {
            return '';
        }
        $spec = $albums[ $k ];
        $opts = array_merge( array(
            'color'       => $spec['color'],
            'height'      => $spec['height'],
            'visual'      => $spec['visual'],
            'attribution' => array(
                'author_name' => self::ARTIST_NAME,
                'author_url'  => self::ARTIST_URL,
                'title'       => $spec['title'],
                'title_url'   => $spec['set_url'],
            ),
        ), $opts );
        return self::embed( self::playlist_resource_url( $spec['playlist_id'] ), $opts );
    }

    // The highlights: the rage.pythai.net story this player promotes.
    const ARTICLE_URL  = 'https://rage.pythai.net/take-it-own-it-codephreak/';
    const DEFAULT_ALBUM = 'music4robots2dance2';

    /**
     * Pro player: an enhanced wrapper the m4r2d2-player.js upgrades with a custom
     * control bar / lazy facade / sticky dock. Progressive enhancement — the raw
     * SoundCloud iframe renders and plays even with JS off (unless lazy).
     *
     * $a accepts: album, url, playlist, track, color, height, visual, theme,
     * controls, sticky, lazy, story, story_label, title, artist, autoplay.
     */
    public static function player_html( $a ) {
        $albums = self::albums();
        $key    = isset( $a['album'] ) && $a['album'] !== '' ? strtolower( $a['album'] ) : '';
        // Resolve the resource + sensible defaults from the album (highlights default).
        $spec = isset( $albums[ $key ] ) ? $albums[ $key ] : null;
        if ( empty( $a['url'] ) && empty( $a['playlist'] ) && empty( $a['track'] ) && ! $spec ) {
            $spec = $albums[ self::DEFAULT_ALBUM ];   // zero-config → the highlights
        }

        if ( ! empty( $a['url'] ) ) {
            $resource = $a['url'];
            $is_set   = ( false !== strpos( $a['url'], '/sets/' ) );
            $def_h    = $is_set ? self::HEIGHT_PLAYLIST : self::HEIGHT_TRACK;
        } elseif ( ! empty( $a['track'] ) ) {
            $resource = self::track_resource_url( $a['track'] );
            $def_h    = self::HEIGHT_TRACK;
        } elseif ( ! empty( $a['playlist'] ) ) {
            $resource = self::playlist_resource_url( $a['playlist'] );
            $def_h    = self::HEIGHT_PLAYLIST;
        } else {
            $resource = self::playlist_resource_url( $spec['playlist_id'] );
            $def_h    = $spec['height'];
        }

        $visual  = isset( $a['visual'] ) ? (bool) $a['visual'] : ( $spec ? $spec['visual'] : false );
        $color   = ! empty( $a['color'] ) ? $a['color'] : ( $spec ? $spec['color'] : self::COLOR_DEFAULT );
        $height  = ! empty( $a['height'] ) ? (int) $a['height'] : $def_h;
        $theme   = ( isset( $a['theme'] ) && $a['theme'] === 'light' ) ? 'light' : 'dark';
        $controls = ! isset( $a['controls'] ) || $a['controls'];   // default ON
        $sticky  = ! empty( $a['sticky'] );
        $lazy    = ! empty( $a['lazy'] );
        $autoplay = ! empty( $a['autoplay'] );
        $title   = isset( $a['title'] ) && $a['title'] !== '' ? $a['title'] : ( $spec ? $spec['title'] : '' );
        $artist  = isset( $a['artist'] ) && $a['artist'] !== '' ? $a['artist'] : self::ARTIST_NAME;
        // story default ON (the highlights link); set story="" to suppress.
        $story   = array_key_exists( 'story', $a ) ? $a['story'] : self::ARTICLE_URL;
        $story_label = ! empty( $a['story_label'] ) ? $a['story_label'] : '▶ the story';

        $src = self::build_player_url( $resource, array(
            'color' => $color, 'visual' => $visual, 'auto_play' => $autoplay,
        ) );

        $b = function ( $v ) { return $v ? 'true' : 'false'; };
        $attrs = array(
            'class'           => 'm4r2d2-embed',
            'data-enhanced'   => '1',
            'data-theme'      => $theme,
            'data-controls'   => $b( $controls ),
            'data-sticky'     => $b( $sticky ),
            'data-lazy'       => $b( $lazy ),
            'data-autoplay'   => $b( $autoplay ),
            'data-title'      => $title,
            'data-artist'     => $artist,
            'data-story'      => $story,
            'data-story-label'=> $story_label,
            'data-src'        => $src,
            'data-height'     => (string) $height,
        );
        $open = '<div';
        foreach ( $attrs as $k => $v ) {
            $open .= ' ' . $k . '="' . esc_attr( $v ) . '"';
        }
        $open .= '>';

        // Progressive enhancement: render the iframe unless lazy (JS builds facade).
        $inner = '';
        if ( ! $lazy ) {
            $inner = sprintf(
                '<iframe class="m4r2d2__iframe" width="100%%" height="%d" scrolling="no" '
                . 'frameborder="no" allow="autoplay; encrypted-media" loading="lazy" '
                . 'title="%s" src="%s"></iframe>',
                $height, esc_attr( $title . ( $artist ? ' — ' . $artist : '' ) ), esc_url( $src )
            );
        }
        return $open . $inner . '</div>';
    }
}
