<?php
/**
 * Plugin Name: Montagne & Paesi - Foto del Giorno Meta
 * Description: Salva automaticamente autore, Instagram, luogo, provincia e data delle foto inviate dal Raspberry tramite Postie come custom field WordPress utilizzabili da Elementor. Gestisce anche la query dell'archivio Foto del Giorno.
 * Version: 1.3.0
 * Author: Montagne & Paesi
 */

if (!defined('ABSPATH')) { exit; }

function mp_fdg_save_fields($post_id, $fields) {
    $allowed = array('foto_autore', 'foto_instagram', 'foto_instagram_url', 'foto_luogo', 'foto_provincia', 'foto_data');
    foreach ($allowed as $key) {
        if (isset($fields[$key]) && trim((string) $fields[$key]) !== '') {
            $value = (string) $fields[$key];
            if ($key === 'foto_instagram_url') {
                $value = esc_url_raw($value);
            } else {
                $value = sanitize_text_field($value);
            }
            update_post_meta($post_id, $key, $value);
        }
    }

    $username = (string) get_post_meta($post_id, 'foto_instagram', true);
    if ($username !== '' && get_post_meta($post_id, 'foto_instagram_url', true) === '') {
        $username = ltrim(trim($username), '@');
        if (preg_match('/^[A-Za-z0-9._]{1,30}$/', $username)) {
            update_post_meta($post_id, 'foto_instagram_url', 'https://www.instagram.com/' . rawurlencode($username) . '/');
        }
    }
}

function mp_fdg_extract_v2($content) {
    if (!preg_match('/<!--\s*FOTO_DEL_GIORNO_META_V2:([A-Za-z0-9+\/=]+)\s*-->/', $content, $match)) {
        return null;
    }
    $decoded = base64_decode($match[1], true);
    if ($decoded === false) {
        return null;
    }
    $data = json_decode($decoded, true);
    return is_array($data) ? $data : null;
}

function mp_fdg_extract_legacy($content) {
    if (!preg_match('/<!--\s*FOTO_DEL_GIORNO_META\s*(.*?)\s*\/FOTO_DEL_GIORNO_META\s*-->/s', $content, $match)) {
        return null;
    }

    $payload = html_entity_decode($match[1], ENT_QUOTES | ENT_HTML5, 'UTF-8');
    $keys = array('foto_autore', 'foto_instagram', 'foto_instagram_url', 'foto_luogo', 'foto_provincia', 'foto_data');
    $fields = array();

    foreach ($keys as $index => $key) {
        $next_keys = array_slice($keys, $index + 1);
        $escaped = array_map(function($v) { return preg_quote($v, '/'); }, $next_keys);
        $end = $next_keys ? '(?=\s*(?:' . implode('|', $escaped) . ')=|$)' : '$';
        if (preg_match('/(?:^|\s)' . preg_quote($key, '/') . '=\s*(.*?)' . $end . '/s', $payload, $m)) {
            $fields[$key] = trim($m[1]);
        }
    }
    return $fields ?: null;
}

function mp_fdg_repair_broken_meta($post_id) {
    $author = (string) get_post_meta($post_id, 'foto_autore', true);
    if ($author === '' || (strpos($author, 'foto_luogo=') === false && strpos($author, 'foto_provincia=') === false && strpos($author, 'foto_data=') === false)) {
        return;
    }

    $payload = 'foto_autore=' . $author;
    $keys = array('foto_autore', 'foto_instagram', 'foto_instagram_url', 'foto_luogo', 'foto_provincia', 'foto_data');
    $fields = array();

    foreach ($keys as $index => $key) {
        $next_keys = array_slice($keys, $index + 1);
        $escaped = array_map(function($v) { return preg_quote($v, '/'); }, $next_keys);
        $end = $next_keys ? '(?=\s*(?:' . implode('|', $escaped) . ')=|$)' : '$';
        if (preg_match('/(?:^|\s)' . preg_quote($key, '/') . '=\s*(.*?)' . $end . '/s', $payload, $m)) {
            $fields[$key] = trim($m[1]);
        }
    }

    if ($fields) {
        mp_fdg_save_fields($post_id, $fields);
    }
}

function mp_fdg_extract_meta($post_id) {
    if (wp_is_post_revision($post_id) || get_post_type($post_id) !== 'post') {
        return;
    }

    $content = get_post_field('post_content', $post_id);
    if (!$content) {
        mp_fdg_repair_broken_meta($post_id);
        return;
    }

    $fields = mp_fdg_extract_v2($content);
    if (!$fields) {
        $fields = mp_fdg_extract_legacy($content);
    }

    if ($fields) {
        mp_fdg_save_fields($post_id, $fields);
    }

    mp_fdg_repair_broken_meta($post_id);

    $clean = preg_replace(array(
        '/<!--\s*FOTO_DEL_GIORNO_META_V2:[A-Za-z0-9+\/=]+\s*-->/',
        '/<!--\s*FOTO_DEL_GIORNO_META\s*.*?\s*\/FOTO_DEL_GIORNO_META\s*-->/s'
    ), '', $content);

    if ($clean !== $content) {
        remove_action('save_post', 'mp_fdg_extract_meta', 20);
        wp_update_post(array('ID' => $post_id, 'post_content' => $clean));
        add_action('save_post', 'mp_fdg_extract_meta', 20);
    }
}
add_action('save_post', 'mp_fdg_extract_meta', 20);

function mp_fdg_postie_after($post) {
    $post_id = 0;
    if (is_numeric($post)) {
        $post_id = (int) $post;
    } elseif (is_array($post) && !empty($post['ID'])) {
        $post_id = (int) $post['ID'];
    } elseif (is_object($post) && !empty($post->ID)) {
        $post_id = (int) $post->ID;
    }
    if ($post_id) {
        mp_fdg_extract_meta($post_id);
    }
    return $post;
}
add_filter('postie_post_after', 'mp_fdg_postie_after', 10, 1);

function mp_fdg_instagram_link_shortcode($atts = array()) {
    $post_id = get_the_ID();
    if (!$post_id) {
        return '';
    }

    $username = trim((string) get_post_meta($post_id, 'foto_instagram', true));
    if ($username === '') {
        return '';
    }
    $username = ltrim($username, '@');

    $url = trim((string) get_post_meta($post_id, 'foto_instagram_url', true));
    if ($url === '') {
        $url = 'https://www.instagram.com/' . rawurlencode($username) . '/';
    }

    return '<a class="mp-fdg-instagram" href="' . esc_url($url) . '" target="_blank" rel="noopener noreferrer">@' . esc_html($username) . '</a>';
}
add_shortcode('foto_instagram_link', 'mp_fdg_instagram_link_shortcode');

/**
 * Elementor Loop Grid: salta il post più recente perché è già mostrato
 * nella sezione principale "La foto del giorno".
 * In Elementor impostare ID Query: foto_del_giorno_archivio
 */
function mp_fdg_elementor_archive_offset($query) {
    $query->set('offset', 1);
}
add_action('elementor/query/foto_del_giorno_archivio', 'mp_fdg_elementor_archive_offset');
