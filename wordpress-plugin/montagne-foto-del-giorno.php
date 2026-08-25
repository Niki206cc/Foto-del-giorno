<?php
/**
 * Plugin Name: Montagne & Paesi - Foto del Giorno Meta
 * Description: Salva automaticamente autore, luogo, provincia e data delle foto inviate dal Raspberry tramite Postie come custom field WordPress utilizzabili da Elementor.
 * Version: 1.1.0
 * Author: Montagne & Paesi
 */

if (!defined('ABSPATH')) { exit; }

function mp_fdg_save_fields($post_id, $fields) {
    $allowed = array('foto_autore', 'foto_luogo', 'foto_provincia', 'foto_data');
    foreach ($allowed as $key) {
        if (isset($fields[$key]) && trim((string) $fields[$key]) !== '') {
            update_post_meta($post_id, $key, sanitize_text_field($fields[$key]));
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
    $keys = array('foto_autore', 'foto_luogo', 'foto_provincia', 'foto_data');
    $fields = array();

    foreach ($keys as $index => $key) {
        $next_keys = array_slice($keys, $index + 1);
        $end = $next_keys ? '(?=\s*(?:' . implode('|', array_map('preg_quote', $next_keys)) . ')=|$)' : '$';
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
    $keys = array('foto_autore', 'foto_luogo', 'foto_provincia', 'foto_data');
    $fields = array();

    foreach ($keys as $index => $key) {
        $next_keys = array_slice($keys, $index + 1);
        $end = $next_keys ? '(?=\s*(?:' . implode('|', array_map('preg_quote', $next_keys)) . ')=|$)' : '$';
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
