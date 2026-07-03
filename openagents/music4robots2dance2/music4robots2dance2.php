<?php
/**
 * Plugin Name:       music4robots2dance2
 * Plugin URI:        https://github.com/gnugui/music4robots2dance2
 * Description:        A complete, forkable SoundCloud interface for WordPress — shortcode, Gutenberg block, oEmbed, and a cypherpunk2048-styled player. Built to support https://rage.pythai.net/take-it-own-it-codephreak/ . take it, own it, use it, share it.
 * Version:           1.0.0
 * Requires at least: 5.8
 * Requires PHP:      7.2
 * Author:            cypherpunk2048 / codephreak
 * Author URI:        https://rage.pythai.net
 * License:           GPL-3.0-or-later
 * License URI:       https://www.gnu.org/licenses/gpl-3.0.html
 * Text Domain:       music4robots2dance2
 *
 * music4robots2dance2 — music for robots to dance to.
 * Copyright (C) 2026 cypherpunk2048 / codephreak.
 *
 * This program is free software: you can redistribute it and/or modify it under
 * the terms of the GNU General Public License as published by the Free Software
 * Foundation, either version 3 of the License, or (at your option) any later
 * version. Distributed WITHOUT ANY WARRANTY. See <https://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // No direct access.
}

define( 'M4R2D2_VERSION', '1.0.0' );
define( 'M4R2D2_URL', plugin_dir_url( __FILE__ ) );
define( 'M4R2D2_DEFAULT_TRACK', 'https://soundcloud.com/codephreak' );

/**
 * Build the SoundCloud player iframe for a track / playlist / user URL.
 *
 * @param array $atts {
 *   @type string $url     SoundCloud URL (track, set, or user). Required.
 *   @type string $color   Hex accent (without #). Default d4af37 (gold).
 *   @type string $height  Pixel height. Default 360 (166 if visual=false).
 *   @type bool   $visual  Big artwork player. Default true.
 *   @type bool   $autoplay Default false (robots ask first).
 * }
 * @return string Sanitized HTML.
 */
function m4r2d2_render( $atts = array() ) {
	$opts = m4r2d2_options();
	$atts = shortcode_atts(
		array(
			'url'      => $opts['default_url'],
			'color'    => $opts['color'],
			'height'   => '',
			'visual'   => $opts['visual'] ? 'true' : 'false',
			'autoplay' => 'false',
			'title'    => '',
		),
		$atts,
		'music4robots2dance2'
	);

	$url = esc_url_raw( trim( $atts['url'] ) );
	if ( empty( $url ) || false === strpos( $url, 'soundcloud.com' ) ) {
		return '<div class="m4r2d2 m4r2d2-error">music4robots2dance2: a soundcloud.com URL is required.</div>';
	}

	$visual   = ( 'true' === (string) $atts['visual'] ) ? 'true' : 'false';
	$autoplay = ( 'true' === (string) $atts['autoplay'] ) ? 'true' : 'false';
	$color    = preg_replace( '/[^0-9a-fA-F]/', '', (string) $atts['color'] );
	$color    = $color ? $color : 'd4af37';
	$height   = (int) $atts['height'];
	if ( $height <= 0 ) {
		$height = ( 'true' === $visual ) ? 360 : 166;
	}

	$player = add_query_arg(
		array(
			'url'                => $url,
			'color'              => '#' . $color,
			'auto_play'          => $autoplay,
			'hide_related'       => 'true',
			'show_comments'      => 'false',
			'show_user'          => 'true',
			'show_reposts'       => 'false',
			'show_teaser'        => 'false',
			'visual'             => $visual,
		),
		'https://w.soundcloud.com/player/'
	);

	$title = $atts['title'] ? esc_html( $atts['title'] ) : '';
	$label = $title ? '<div class="m4r2d2-title">' . $title . '</div>' : '';

	$iframe = sprintf(
		'<iframe class="m4r2d2-player" width="100%%" height="%d" scrolling="no" frameborder="no" allow="autoplay" loading="lazy" src="%s"></iframe>',
		$height,
		esc_url( $player )
	);

	return '<div class="m4r2d2">' . $label . $iframe
		. '<div class="m4r2d2-foot">music4robots2dance2 · <a href="' . esc_url( $url ) . '" rel="noopener" target="_blank">listen on SoundCloud</a> · <em>take it, own it, use it, share it</em></div></div>';
}

/* ---- Shortcodes: [music4robots2dance2], [m4r2d2], [soundcloud] ---- */
add_shortcode( 'music4robots2dance2', 'm4r2d2_render' );
add_shortcode( 'm4r2d2', 'm4r2d2_render' );
add_shortcode( 'soundcloud', 'm4r2d2_render' );

/* ---- Assets ---- */
function m4r2d2_assets() {
	wp_register_style( 'm4r2d2', M4R2D2_URL . 'assets/m4r2d2.css', array(), M4R2D2_VERSION );
	wp_enqueue_style( 'm4r2d2' );
}
add_action( 'wp_enqueue_scripts', 'm4r2d2_assets' );

/* ---- Gutenberg block (server-rendered; no build step, stays forkable) ---- */
function m4r2d2_register_block() {
	if ( ! function_exists( 'register_block_type' ) ) {
		return;
	}
	register_block_type(
		'm4r2d2/player',
		array(
			'api_version'     => 2,
			'editor_script'   => 'm4r2d2-block',
			'style'           => 'm4r2d2',
			'render_callback' => 'm4r2d2_render',
			'attributes'      => array(
				'url'      => array( 'type' => 'string', 'default' => M4R2D2_DEFAULT_TRACK ),
				'color'    => array( 'type' => 'string', 'default' => 'd4af37' ),
				'height'   => array( 'type' => 'string', 'default' => '' ),
				'visual'   => array( 'type' => 'string', 'default' => 'true' ),
				'autoplay' => array( 'type' => 'string', 'default' => 'false' ),
				'title'    => array( 'type' => 'string', 'default' => '' ),
			),
		)
	);
	wp_register_script(
		'm4r2d2-block',
		M4R2D2_URL . 'assets/block.js',
		array( 'wp-blocks', 'wp-element', 'wp-block-editor', 'wp-components' ),
		M4R2D2_VERSION,
		true
	);
}
add_action( 'init', 'm4r2d2_register_block' );

/* ---- oEmbed: SoundCloud is already whitelisted by core; make sure of it ---- */
function m4r2d2_oembed() {
	if ( function_exists( 'wp_oembed_add_provider' ) ) {
		wp_oembed_add_provider( '#https?://(www\.)?soundcloud\.com/.*#i', 'https://soundcloud.com/oembed', true );
	}
}
add_action( 'init', 'm4r2d2_oembed' );

/* ---- Settings (Settings → music4robots2dance2) ---- */
function m4r2d2_options() {
	$defaults = array(
		'default_url' => M4R2D2_DEFAULT_TRACK,
		'color'       => 'd4af37',
		'visual'      => 1,
	);
	return wp_parse_args( get_option( 'm4r2d2_options', array() ), $defaults );
}

function m4r2d2_settings_init() {
	register_setting( 'm4r2d2', 'm4r2d2_options', 'm4r2d2_sanitize' );
	add_settings_section( 'm4r2d2_main', __( 'Defaults', 'music4robots2dance2' ), '__return_false', 'm4r2d2' );
	add_settings_field( 'default_url', __( 'Default SoundCloud URL', 'music4robots2dance2' ), 'm4r2d2_field_url', 'm4r2d2', 'm4r2d2_main' );
	add_settings_field( 'color', __( 'Accent colour (hex, no #)', 'music4robots2dance2' ), 'm4r2d2_field_color', 'm4r2d2', 'm4r2d2_main' );
}
add_action( 'admin_init', 'm4r2d2_settings_init' );

function m4r2d2_sanitize( $in ) {
	return array(
		'default_url' => esc_url_raw( isset( $in['default_url'] ) ? $in['default_url'] : M4R2D2_DEFAULT_TRACK ),
		'color'       => preg_replace( '/[^0-9a-fA-F]/', '', isset( $in['color'] ) ? $in['color'] : 'd4af37' ),
		'visual'      => 1,
	);
}

function m4r2d2_field_url() {
	$o = m4r2d2_options();
	printf( '<input type="url" name="m4r2d2_options[default_url]" value="%s" class="regular-text" />', esc_attr( $o['default_url'] ) );
}
function m4r2d2_field_color() {
	$o = m4r2d2_options();
	printf( '<input type="text" name="m4r2d2_options[color]" value="%s" class="small-text" />', esc_attr( $o['color'] ) );
}

function m4r2d2_settings_page() {
	add_options_page( 'music4robots2dance2', 'music4robots2dance2', 'manage_options', 'm4r2d2', 'm4r2d2_settings_html' );
}
add_action( 'admin_menu', 'm4r2d2_settings_page' );

function m4r2d2_settings_html() {
	if ( ! current_user_can( 'manage_options' ) ) {
		return;
	}
	echo '<div class="wrap"><h1>music4robots2dance2</h1>';
	echo '<p>A complete, forkable SoundCloud interface. Use <code>[music4robots2dance2 url="…"]</code>, <code>[soundcloud url="…"]</code>, the <strong>m4r2d2 player</strong> block, or just paste a SoundCloud link (oEmbed). <em>take it, own it, use it, share it.</em></p>';
	echo '<form action="options.php" method="post">';
	settings_fields( 'm4r2d2' );
	do_settings_sections( 'm4r2d2' );
	submit_button();
	echo '</form></div>';
}
