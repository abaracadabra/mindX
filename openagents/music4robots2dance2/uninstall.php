<?php
// music4robots2dance2 uninstall — remove our single option. GPL-3.0-or-later.
if ( ! defined( 'WP_UNINSTALL_PLUGIN' ) ) { exit; }
delete_option( 'm4r2d2_options' );
