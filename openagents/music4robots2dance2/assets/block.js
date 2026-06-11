/* music4robots2dance2 — Gutenberg block (server-rendered, no build step). GPL-3.0-or-later. */
( function ( blocks, element, blockEditor, components ) {
	'use strict';
	var el = element.createElement;
	var InspectorControls = blockEditor.InspectorControls;
	var useBlockProps = blockEditor.useBlockProps;
	var TextControl = components.TextControl;
	var PanelBody = components.PanelBody;
	var ToggleControl = components.ToggleControl;

	blocks.registerBlockType( 'm4r2d2/player', {
		title: 'm4r2d2 player',
		description: 'A SoundCloud player — music for robots to dance to.',
		icon: 'format-audio',
		category: 'embed',
		attributes: {
			url: { type: 'string', default: 'https://soundcloud.com/codephreak' },
			color: { type: 'string', default: 'd4af37' },
			title: { type: 'string', default: '' },
			visual: { type: 'string', default: 'true' },
			autoplay: { type: 'string', default: 'false' }
		},
		edit: function ( props ) {
			var a = props.attributes;
			var set = props.setAttributes;
			return el(
				'div',
				useBlockProps(),
				el(
					InspectorControls,
					{},
					el(
						PanelBody,
						{ title: 'music4robots2dance2', initialOpen: true },
						el( TextControl, {
							label: 'SoundCloud URL',
							value: a.url,
							onChange: function ( v ) { set( { url: v } ); }
						} ),
						el( TextControl, {
							label: 'Title (optional)',
							value: a.title,
							onChange: function ( v ) { set( { title: v } ); }
						} ),
						el( TextControl, {
							label: 'Accent colour (hex, no #)',
							value: a.color,
							onChange: function ( v ) { set( { color: v } ); }
						} ),
						el( ToggleControl, {
							label: 'Visual (big artwork) player',
							checked: a.visual === 'true',
							onChange: function ( v ) { set( { visual: v ? 'true' : 'false' } ); }
						} ),
						el( ToggleControl, {
							label: 'Autoplay',
							checked: a.autoplay === 'true',
							onChange: function ( v ) { set( { autoplay: v ? 'true' : 'false' } ); }
						} )
					)
				),
				el(
					'div',
					{ style: { padding: '12px', border: '1px solid #d4af37', borderRadius: '10px', background: '#0a0a12', color: '#d4af37', fontFamily: 'monospace' } },
					'♪ m4r2d2 player — ' + ( a.url || 'set a SoundCloud URL' )
				)
			);
		},
		save: function () { return null; } // server-rendered via render_callback
	} );
} )( window.wp.blocks, window.wp.element, window.wp.blockEditor, window.wp.components );
