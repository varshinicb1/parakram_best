/**
 * @file ble_crypto.h
 * @brief End-to-end encryption for BLE provisioning — X25519 + AES-256-GCM.
 */
#pragma once

#include "esp_err.h"
#include <stddef.h>
#include <stdint.h>

#define BLE_CRYPTO_PUBKEY_LEN  32
#define BLE_CRYPTO_GCM_IV_LEN  12
#define BLE_CRYPTO_GCM_TAG_LEN 16

/** Generate X25519 keypair. Call once at boot. */
esp_err_t ble_crypto_init(void);

/** Returns pointer to 32-byte local public key (advertised in BLE characteristic). */
const uint8_t *ble_crypto_get_pubkey(void);

/** Set peer (phone) public key and derive shared AES-256-GCM key via ECDH + HKDF. */
esp_err_t ble_crypto_set_peer_key(const uint8_t *peer_pubkey, size_t len);

/** Decrypt BLE payload: [12B IV][16B tag][ciphertext] → plaintext. */
esp_err_t ble_crypto_decrypt(const uint8_t *ciphertext, size_t ct_len,
                              uint8_t *plaintext, size_t *pt_len);

/** Encrypt data for BLE response: plaintext → [12B IV][16B tag][ciphertext]. */
esp_err_t ble_crypto_encrypt(const uint8_t *plaintext, size_t pt_len,
                              uint8_t *ciphertext, size_t *ct_len);

/** Free all crypto resources. */
void ble_crypto_deinit(void);
