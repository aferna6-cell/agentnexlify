<?php
/**
 * Plugin Name:       AgentNexLiFy Chat Widget
 * Plugin URI:        https://agentnexlify.com
 * Description:       One-click install for the AgentNexLiFy AI chat widget. Paste your widget key, save, and the assistant goes live on your site — no theme editing, no code.
 * Version:           1.0.0
 * Requires at least: 5.8
 * Requires PHP:      7.2
 * Author:            AgentNexLiFy
 * Author URI:        https://agentnexlify.com
 * License:           GPL-2.0-or-later
 * License URI:       https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain:       agentnexlify
 *
 * The owner pastes their public widget key (wk_...). This plugin injects the
 * exact same loader snippet shown in the dashboard embed step — byte-identical
 * to the hand-pasted <script> tag — into wp_footer, just before </body>.
 *
 * The widget key is a PUBLIC, per-tenant key meant to live on the owner's site.
 * It is not a secret; storing it in wp_options is correct. No private/service
 * keys are ever handled by this plugin.
 */

// Block direct access.
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

define( 'AGENTNEXLIFY_VERSION', '1.0.0' );
define( 'AGENTNEXLIFY_OPTION', 'agentnexlify_settings' );

/**
 * Canonical loader URL. Serving the loader from app.agentnexlify.com lets the
 * widget auto-derive its API base from the script host (see loader:
 * data-api-base falls back to script.src host). Owners on a custom/self-host
 * deployment can override both fields below.
 */
define( 'AGENTNEXLIFY_DEFAULT_LOADER', 'https://app.agentnexlify.com/widget/agentnexlify-widget.js' );

/**
 * Default settings shape.
 *
 * @return array
 */
function agentnexlify_default_settings() {
	return array(
		'api_key'     => '',
		'brand_color' => '',
		'loader_url'  => AGENTNEXLIFY_DEFAULT_LOADER,
		'api_base'    => '',
		'enabled'     => '1',
	);
}

/**
 * Read merged settings (stored over defaults).
 *
 * @return array
 */
function agentnexlify_get_settings() {
	$saved = get_option( AGENTNEXLIFY_OPTION, array() );
	if ( ! is_array( $saved ) ) {
		$saved = array();
	}
	return wp_parse_args( $saved, agentnexlify_default_settings() );
}

/* -------------------------------------------------------------------------
 * Settings page (Settings → AgentNexLiFy)
 * ---------------------------------------------------------------------- */

add_action( 'admin_menu', 'agentnexlify_admin_menu' );
function agentnexlify_admin_menu() {
	add_options_page(
		__( 'AgentNexLiFy Chat Widget', 'agentnexlify' ),
		__( 'AgentNexLiFy', 'agentnexlify' ),
		'manage_options',
		'agentnexlify',
		'agentnexlify_settings_page'
	);
}

add_action( 'admin_init', 'agentnexlify_register_settings' );
function agentnexlify_register_settings() {
	register_setting(
		'agentnexlify_group',
		AGENTNEXLIFY_OPTION,
		array(
			'type'              => 'array',
			'sanitize_callback' => 'agentnexlify_sanitize_settings',
			'default'           => agentnexlify_default_settings(),
		)
	);
}

/**
 * Sanitize every field. Output is later escaped again at render time
 * (defense in depth). The API key is restricted to the character set our
 * keys actually use.
 *
 * @param array $input Raw form input.
 * @return array
 */
function agentnexlify_sanitize_settings( $input ) {
	$clean = agentnexlify_default_settings();

	if ( ! is_array( $input ) ) {
		return $clean;
	}

	// Widget API key: alphanumeric, underscore, hyphen only.
	if ( isset( $input['api_key'] ) ) {
		$clean['api_key'] = preg_replace( '/[^A-Za-z0-9_\-]/', '', (string) $input['api_key'] );
	}

	// Brand color: hex like #6cff5c (optional). Empty = use loader default.
	if ( isset( $input['brand_color'] ) ) {
		$color = trim( (string) $input['brand_color'] );
		if ( '' === $color || preg_match( '/^#[0-9A-Fa-f]{6}$/', $color ) ) {
			$clean['brand_color'] = $color;
		} else {
			add_settings_error(
				AGENTNEXLIFY_OPTION,
				'brand_color',
				__( 'Brand color must be a 6-digit hex value like #6cff5c. Ignored.', 'agentnexlify' ),
				'warning'
			);
			$clean['brand_color'] = '';
		}
	}

	// Loader URL: must be a valid https URL. Fall back to default if blank/invalid.
	if ( isset( $input['loader_url'] ) ) {
		$url = esc_url_raw( trim( (string) $input['loader_url'] ), array( 'https' ) );
		$clean['loader_url'] = $url ? $url : AGENTNEXLIFY_DEFAULT_LOADER;
	}

	// Optional API base override: valid https URL or blank.
	if ( isset( $input['api_base'] ) && '' !== trim( (string) $input['api_base'] ) ) {
		$base = esc_url_raw( trim( (string) $input['api_base'] ), array( 'https' ) );
		$clean['api_base'] = $base ? $base : '';
	} else {
		$clean['api_base'] = '';
	}

	$clean['enabled'] = ( isset( $input['enabled'] ) && '1' === (string) $input['enabled'] ) ? '1' : '0';

	return $clean;
}

function agentnexlify_settings_page() {
	if ( ! current_user_can( 'manage_options' ) ) {
		return;
	}

	$settings = agentnexlify_get_settings();
	$preview  = agentnexlify_build_snippet( $settings );
	?>
	<div class="wrap">
		<h1><?php echo esc_html__( 'AgentNexLiFy Chat Widget', 'agentnexlify' ); ?></h1>
		<p style="max-width:680px;">
			<?php echo esc_html__( 'Paste your widget key from the AgentNexLiFy dashboard (Onboarding → "Your embed code", or Widget settings). Save, and the chat assistant appears on every page. No theme editing needed.', 'agentnexlify' ); ?>
		</p>

		<form method="post" action="options.php">
			<?php settings_fields( 'agentnexlify_group' ); ?>
			<table class="form-table" role="presentation">
				<tr>
					<th scope="row">
						<label for="agentnexlify_api_key"><?php echo esc_html__( 'Widget key', 'agentnexlify' ); ?></label>
					</th>
					<td>
						<input
							name="<?php echo esc_attr( AGENTNEXLIFY_OPTION ); ?>[api_key]"
							id="agentnexlify_api_key"
							type="text"
							class="regular-text code"
							value="<?php echo esc_attr( $settings['api_key'] ); ?>"
							placeholder="wk_xxxxxxxxxxxxxxxx"
							autocomplete="off"
						/>
						<p class="description"><?php echo esc_html__( 'Starts with "wk_". This is your public widget key, safe to publish on your site.', 'agentnexlify' ); ?></p>
					</td>
				</tr>

				<tr>
					<th scope="row"><?php echo esc_html__( 'Show widget', 'agentnexlify' ); ?></th>
					<td>
						<label>
							<input
								name="<?php echo esc_attr( AGENTNEXLIFY_OPTION ); ?>[enabled]"
								type="checkbox"
								value="1"
								<?php checked( '1', $settings['enabled'] ); ?>
							/>
							<?php echo esc_html__( 'Load the chat widget on the front end of my site', 'agentnexlify' ); ?>
						</label>
					</td>
				</tr>

				<tr>
					<th scope="row">
						<label for="agentnexlify_brand_color"><?php echo esc_html__( 'Brand color', 'agentnexlify' ); ?></label>
					</th>
					<td>
						<input
							name="<?php echo esc_attr( AGENTNEXLIFY_OPTION ); ?>[brand_color]"
							id="agentnexlify_brand_color"
							type="text"
							class="regular-text code"
							value="<?php echo esc_attr( $settings['brand_color'] ); ?>"
							placeholder="#6cff5c"
						/>
						<p class="description"><?php echo esc_html__( 'Optional. Hex like #6cff5c. Leave blank to use your dashboard branding.', 'agentnexlify' ); ?></p>
					</td>
				</tr>
			</table>

			<h2 class="title"><?php echo esc_html__( 'Advanced', 'agentnexlify' ); ?></h2>
			<p class="description" style="max-width:680px;"><?php echo esc_html__( 'Most owners never touch these. Only change them if AgentNexLiFy support tells you to (e.g. a self-hosted deployment).', 'agentnexlify' ); ?></p>
			<table class="form-table" role="presentation">
				<tr>
					<th scope="row">
						<label for="agentnexlify_loader_url"><?php echo esc_html__( 'Loader URL', 'agentnexlify' ); ?></label>
					</th>
					<td>
						<input
							name="<?php echo esc_attr( AGENTNEXLIFY_OPTION ); ?>[loader_url]"
							id="agentnexlify_loader_url"
							type="url"
							class="regular-text code"
							value="<?php echo esc_attr( $settings['loader_url'] ); ?>"
							placeholder="<?php echo esc_attr( AGENTNEXLIFY_DEFAULT_LOADER ); ?>"
						/>
					</td>
				</tr>
				<tr>
					<th scope="row">
						<label for="agentnexlify_api_base"><?php echo esc_html__( 'API base override', 'agentnexlify' ); ?></label>
					</th>
					<td>
						<input
							name="<?php echo esc_attr( AGENTNEXLIFY_OPTION ); ?>[api_base]"
							id="agentnexlify_api_base"
							type="url"
							class="regular-text code"
							value="<?php echo esc_attr( $settings['api_base'] ); ?>"
							placeholder="https://app.agentnexlify.com"
						/>
						<p class="description"><?php echo esc_html__( 'Optional. Leave blank — the widget derives this from the loader URL automatically.', 'agentnexlify' ); ?></p>
					</td>
				</tr>
			</table>

			<?php submit_button(); ?>
		</form>

		<h2><?php echo esc_html__( 'This is what gets added to your site', 'agentnexlify' ); ?></h2>
		<?php if ( '' === $settings['api_key'] ) : ?>
			<p><em><?php echo esc_html__( 'Enter your widget key above and save to activate.', 'agentnexlify' ); ?></em></p>
		<?php else : ?>
			<pre style="background:#1d2327;color:#86efac;padding:16px;border-radius:6px;overflow:auto;max-width:680px;"><?php echo esc_html( $preview ); ?></pre>
		<?php endif; ?>
	</div>
	<?php
}

/* -------------------------------------------------------------------------
 * Front-end injection
 * ---------------------------------------------------------------------- */

/**
 * Build the loader <script> tag from settings. Mirrors the dashboard embed
 * snippet: a single async script with data-api-key (+ optional brand color
 * and api base). All values are escaped for HTML attribute context.
 *
 * @param array $settings Merged settings.
 * @return string Empty string when not renderable.
 */
function agentnexlify_build_snippet( $settings ) {
	if ( '1' !== $settings['enabled'] || '' === $settings['api_key'] ) {
		return '';
	}

	$loader = $settings['loader_url'] ? $settings['loader_url'] : AGENTNEXLIFY_DEFAULT_LOADER;

	$attrs  = 'src="' . esc_url( $loader ) . '"';
	$attrs .= ' data-api-key="' . esc_attr( $settings['api_key'] ) . '"';

	if ( '' !== $settings['brand_color'] ) {
		$attrs .= ' data-brand-color="' . esc_attr( $settings['brand_color'] ) . '"';
	}
	if ( '' !== $settings['api_base'] ) {
		$attrs .= ' data-api-base="' . esc_url( $settings['api_base'] ) . '"';
	}

	return '<script ' . $attrs . ' async></script>';
}

add_action( 'wp_footer', 'agentnexlify_render_widget', 99 );
function agentnexlify_render_widget() {
	// Don't load inside the admin or feeds.
	if ( is_admin() || is_feed() ) {
		return;
	}

	$snippet = agentnexlify_build_snippet( agentnexlify_get_settings() );
	if ( '' === $snippet ) {
		return;
	}

	// Snippet is assembled from individually-escaped, sanitized values above.
	echo "\n<!-- AgentNexLiFy Chat Widget -->\n" . $snippet . "\n"; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
}

/* -------------------------------------------------------------------------
 * Settings link on the Plugins screen
 * ---------------------------------------------------------------------- */

add_filter( 'plugin_action_links_' . plugin_basename( __FILE__ ), 'agentnexlify_action_links' );
function agentnexlify_action_links( $links ) {
	$settings_link = '<a href="' . esc_url( admin_url( 'options-general.php?page=agentnexlify' ) ) . '">' . esc_html__( 'Settings', 'agentnexlify' ) . '</a>';
	array_unshift( $links, $settings_link );
	return $links;
}
