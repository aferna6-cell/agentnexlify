<?php
/**
 * Uninstall cleanup for AgentNexLiFy Chat Widget.
 *
 * Runs only when the user deletes the plugin from the WordPress admin.
 * Removes the single option this plugin stores. No widget data lives in
 * WordPress — conversations/leads live in the AgentNexLiFy account.
 */

if ( ! defined( 'WP_UNINSTALL_PLUGIN' ) ) {
	exit;
}

delete_option( 'agentnexlify_settings' );
