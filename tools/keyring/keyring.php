#!/usr/bin/env php
<?php

/*
 * Local keyring for operational credentials.
 * This kit contains no pre-existing keys or secrets.
 */

const KEY_FILE = __DIR__ . '/keyring.key';
const VAULT_FILE = __DIR__ . '/keyring.vault';
const CIPHER = 'aes-256-gcm';

function abortKeyring($message, $code = 1)
{
    fwrite(STDERR, $message . PHP_EOL);
    exit($code);
}

function keyringKey()
{
    if (!is_file(KEY_FILE)) abortKeyring('Keyring key not found.');
    $key = file_get_contents(KEY_FILE);
    if ($key === false || strlen($key) !== 32)
        abortKeyring('Invalid keyring key.');
    return $key;
}

function loadVault()
{
    if (!is_file(VAULT_FILE)) return array();
    $envelope = json_decode(file_get_contents(VAULT_FILE), true);
    if (!is_array($envelope) ||
        !isset($envelope['iv'], $envelope['tag'], $envelope['data']))
        abortKeyring('Damaged keyring.');
    $plain = openssl_decrypt(
        base64_decode($envelope['data'], true),
        CIPHER,
        keyringKey(),
        OPENSSL_RAW_DATA,
        base64_decode($envelope['iv'], true),
        base64_decode($envelope['tag'], true),
        'codex-keyring-v1'
    );
    if ($plain === false) abortKeyring('Unable to decrypt the keyring.');
    $vault = json_decode($plain, true);
    if (!is_array($vault)) abortKeyring('Invalid keyring contents.');
    return $vault;
}

function saveVault($vault)
{
    $iv = random_bytes(openssl_cipher_iv_length(CIPHER));
    $tag = '';
    $data = openssl_encrypt(
        json_encode($vault, JSON_UNESCAPED_SLASHES),
        CIPHER,
        keyringKey(),
        OPENSSL_RAW_DATA,
        $iv,
        $tag,
        'codex-keyring-v1',
        16
    );
    if ($data === false) abortKeyring('Keyring encryption failed.');
    $envelope = json_encode(array(
        'version' => 1,
        'cipher' => CIPHER,
        'iv' => base64_encode($iv),
        'tag' => base64_encode($tag),
        'data' => base64_encode($data)
    ), JSON_UNESCAPED_SLASHES);
    $temporary = VAULT_FILE . '.tmp.' . getmypid();
    if (file_put_contents($temporary, $envelope . PHP_EOL, LOCK_EX) === false)
        abortKeyring('Unable to write the keyring.');
    chmod($temporary, 0600);
    if (!rename($temporary, VAULT_FILE)) {
        @unlink($temporary);
        abortKeyring('Unable to replace the keyring atomically.');
    }
}

function validName($name)
{
    if (!preg_match('/^[a-z0-9][a-z0-9._-]{1,63}$/', $name))
        abortKeyring('Invalid name.');
}

$command = isset($argv[1]) ? $argv[1] : '';
$name = isset($argv[2]) ? $argv[2] : '';

if ($command === 'init') {
    if (!is_file(KEY_FILE)) {
        if (file_put_contents(KEY_FILE, random_bytes(32), LOCK_EX) === false)
            abortKeyring('Key generation failed.');
        chmod(KEY_FILE, 0600);
    }
    if (!is_file(VAULT_FILE)) saveVault(array());
    exit(0);
}

$vault = loadVault();

if ($command === 'list') {
    $names = array_keys($vault);
    sort($names);
    foreach ($names as $item) echo $item . PHP_EOL;
    exit(0);
}

validName($name);

if ($command === 'set') {
    $value = preg_replace('/[\r\n]+$/', '', stream_get_contents(STDIN));
    if ($value === '') abortKeyring('Empty value.');
    $vault[$name] = $value;
    saveVault($vault);
    exit(0);
}

if ($command === 'get') {
    if (!array_key_exists($name, $vault)) abortKeyring('Entry not found.', 2);
    echo $vault[$name];
    exit(0);
}

if ($command === 'delete') {
    if (!array_key_exists($name, $vault)) abortKeyring('Entry not found.', 2);
    unset($vault[$name]);
    saveVault($vault);
    exit(0);
}

abortKeyring("Usage: keyring.php init|list|set NAME|get NAME|delete NAME");
