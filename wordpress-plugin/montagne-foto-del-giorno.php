<?php
/**
 * Plugin Name: Montagne & Paesi - Foto del Giorno Meta
 * Description: Salva automaticamente autore, luogo, provincia e data delle foto inviate dal Raspberry tramite Postie come custom field WordPress utilizzabili da Elementor.
 * Version: 1.0.0
 * Author: Montagne & Paesi
 */

if (!defined('ABSPATH')) { exit; }

function mp_fdg_extract_meta($post_id) {
    if (wp_is_post_revision($post_id) || get_post_type($post_id) !== 'post') {
        return;
    }

    $content = get_post_field('post_content', $post_id);
    if (!$content || strpos($content, 'FOTO_DEL_GIORNO_META') === false) {
        return;
    }

    if (!preg_match('/<!--\s*FOTO_DEL_GIORNO_META\s*(.*?)\s*\/FOTO_DEL_GIORNO_META\s*-->/s', $content, $match)) {
        return;
    }

    $allowed = array('foto_autore', 'foto_luogo', 'foto_provincia', 'foto_data');
    $payload = html_entity_decode($match[1], ENT_QUOTES | ENT_HTML5, 'UTF-8');
    $lines = preg_split('/\R/', trim($payload));

    foreach ($lines as $line) {
        if (strpos($line, '=') === false) { continue; }
        list($key, $value) = array_map('trim', explode('=', $line, 2));
        if (in_array($key, $allowed, true) && $value !== '') {
            update_post_meta($post_id, $key, sanitize_text_field($value));
        }
    }

    // Rimuove il blocco tecnico dal contenuto dopo aver salvato i custom field.
    $clean = preg_replace('/<!--\s*FOTO_DEL_GIORNO_META\s*.*?\s*\/FOTO_DEL_GIORNO_META\s*-->/s', '', $content);
    if ($clean !== $content) {
        remove_action('save_post', 'mp_fdg_extract_meta', 20);
        wp_update_post(array('ID' => $post_id, 'post_content' => $clean));
        add_action('save_post', 'mp_fdg_extract_meta', 20);
    }
}
add_action('save_post', 'mp_fdg_extract_meta', 20);

// Postie espone anche questo hook dopo la creazione del post: lo usiamo come
// seconda possibilità, senza dipendere da add-on commerciali.
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
