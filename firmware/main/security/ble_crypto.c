/**
 * @file ble_crypto.c
 * @brief End-to-end encryption for BLE provisioning — X25519 key exchange + AES-256-GCM.
 *
 * Protects WiFi credentials during BLE provisioning (SoftAP fallback stays unencrypted).
 * Uses mbedTLS (bundled with ESP-IDF) for all cryptographic operations.
 *
 * Flow:
 *   1. Board generates ephemeral X25519 keypair, advertises public key in BLE characteristic
 *   2. Phone generates its own keypair, sends public key over BLE GATT write
 *   3. Both sides compute shared secret via ECDH
 *   4. Shared secret is hashed with HKDF-SHA256 to derive AES-256-GCM key
 *   5. Phone encrypts WiFi SSID+password with AES-GCM, sends ciphertext over BLE
 *   6. Board decrypts and configures WiFi
 */

#include "esp_err.h"
#include "esp_log.h"
#include "esp_random.h"
#include <string.h>

#include "mbedtls/ecdh.h"
#include "mbedtls/gcm.h"
#include "mbedtls/hkdf.h"
#include "mbedtls/md.h"
#include "mbedtls/ctr_drbg.h"
#include "mbedtls/entropy.h"

static const char *TAG = "BLE_CRYPTO";

#define BLE_CRYPTO_PUBKEY_LEN  32
#define BLE_CRYPTO_AES_KEY_LEN 32
#define BLE_CRYPTO_GCM_IV_LEN  12
#define BLE_CRYPTO_GCM_TAG_LEN 16
#define BLE_CRYPTO_MAX_PLAINTEXT 256

typedef struct {
    mbedtls_ecdh_context ecdh;
    mbedtls_ctr_drbg_context ctr_drbg;
    mbedtls_entropy_context entropy;
    uint8_t local_pubkey[BLE_CRYPTO_PUBKEY_LEN];
    uint8_t shared_key[BLE_CRYPTO_AES_KEY_LEN];
    bool key_derived;
    bool initialized;
} ble_crypto_ctx_t;

static ble_crypto_ctx_t s_ctx;

static int esp_rng_wrapper(void *p_rng, unsigned char *output, size_t output_len) {
    (void)p_rng;
    esp_fill_random(output, output_len);
    return 0;
}

esp_err_t ble_crypto_init(void) {
    if (s_ctx.initialized) return ESP_OK;

    memset(&s_ctx, 0, sizeof(s_ctx));

    mbedtls_entropy_init(&s_ctx.entropy);
    mbedtls_ctr_drbg_init(&s_ctx.ctr_drbg);
    mbedtls_ecdh_init(&s_ctx.ecdh);

    int ret = mbedtls_ctr_drbg_seed(&s_ctx.ctr_drbg, esp_rng_wrapper, NULL,
                                     (const unsigned char *)"parakram_ble", 12);
    if (ret != 0) {
        ESP_LOGE(TAG, "ctr_drbg_seed failed: -0x%04x", -ret);
        return ESP_FAIL;
    }

    ret = mbedtls_ecdh_setup(&s_ctx.ecdh, MBEDTLS_ECP_DP_CURVE25519);
    if (ret != 0) {
        ESP_LOGE(TAG, "ecdh_setup failed: -0x%04x", -ret);
        return ESP_FAIL;
    }

    size_t olen = 0;
    uint8_t buf[BLE_CRYPTO_PUBKEY_LEN + 1];
    ret = mbedtls_ecdh_make_public(&s_ctx.ecdh, &olen, buf, sizeof(buf),
                                    mbedtls_ctr_drbg_random, &s_ctx.ctr_drbg);
    if (ret != 0) {
        ESP_LOGE(TAG, "make_public failed: -0x%04x", -ret);
        return ESP_FAIL;
    }

    memcpy(s_ctx.local_pubkey, buf, BLE_CRYPTO_PUBKEY_LEN);
    s_ctx.initialized = true;
    ESP_LOGI(TAG, "X25519 keypair generated");
    return ESP_OK;
}

const uint8_t *ble_crypto_get_pubkey(void) {
    return s_ctx.local_pubkey;
}

esp_err_t ble_crypto_set_peer_key(const uint8_t *peer_pubkey, size_t len) {
    if (!s_ctx.initialized) return ESP_ERR_INVALID_STATE;
    if (len != BLE_CRYPTO_PUBKEY_LEN) return ESP_ERR_INVALID_ARG;

    int ret = mbedtls_ecdh_read_public(&s_ctx.ecdh, peer_pubkey, len);
    if (ret != 0) {
        ESP_LOGE(TAG, "read_public failed: -0x%04x", -ret);
        return ESP_FAIL;
    }

    uint8_t shared_secret[BLE_CRYPTO_PUBKEY_LEN];
    size_t olen = 0;
    ret = mbedtls_ecdh_calc_secret(&s_ctx.ecdh, &olen, shared_secret, sizeof(shared_secret),
                                    mbedtls_ctr_drbg_random, &s_ctx.ctr_drbg);
    if (ret != 0) {
        ESP_LOGE(TAG, "calc_secret failed: -0x%04x", -ret);
        return ESP_FAIL;
    }

    /* HKDF-SHA256: shared_secret → AES-256-GCM key */
    const mbedtls_md_info_t *md = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
    ret = mbedtls_hkdf(md,
                       (const unsigned char *)"parakram-ble-prov", 17,
                       shared_secret, olen,
                       (const unsigned char *)"aes-gcm-key", 11,
                       s_ctx.shared_key, BLE_CRYPTO_AES_KEY_LEN);
    if (ret != 0) {
        ESP_LOGE(TAG, "hkdf failed: -0x%04x", -ret);
        return ESP_FAIL;
    }

    s_ctx.key_derived = true;
    ESP_LOGI(TAG, "Shared key derived via ECDH + HKDF");
    return ESP_OK;
}

esp_err_t ble_crypto_decrypt(const uint8_t *ciphertext, size_t ct_len,
                              uint8_t *plaintext, size_t *pt_len) {
    if (!s_ctx.key_derived) return ESP_ERR_INVALID_STATE;
    if (ct_len < BLE_CRYPTO_GCM_IV_LEN + BLE_CRYPTO_GCM_TAG_LEN + 1) {
        return ESP_ERR_INVALID_ARG;
    }

    const uint8_t *iv = ciphertext;
    const uint8_t *tag = ciphertext + BLE_CRYPTO_GCM_IV_LEN;
    const uint8_t *data = ciphertext + BLE_CRYPTO_GCM_IV_LEN + BLE_CRYPTO_GCM_TAG_LEN;
    size_t data_len = ct_len - BLE_CRYPTO_GCM_IV_LEN - BLE_CRYPTO_GCM_TAG_LEN;

    if (data_len > BLE_CRYPTO_MAX_PLAINTEXT) return ESP_ERR_INVALID_SIZE;

    mbedtls_gcm_context gcm;
    mbedtls_gcm_init(&gcm);

    int ret = mbedtls_gcm_setkey(&gcm, MBEDTLS_CIPHER_ID_AES,
                                  s_ctx.shared_key, BLE_CRYPTO_AES_KEY_LEN * 8);
    if (ret != 0) {
        mbedtls_gcm_free(&gcm);
        return ESP_FAIL;
    }

    ret = mbedtls_gcm_auth_decrypt(&gcm, data_len,
                                    iv, BLE_CRYPTO_GCM_IV_LEN,
                                    NULL, 0,
                                    tag, BLE_CRYPTO_GCM_TAG_LEN,
                                    data, plaintext);
    mbedtls_gcm_free(&gcm);

    if (ret != 0) {
        ESP_LOGE(TAG, "GCM decrypt/verify failed: -0x%04x (tampered?)", -ret);
        return ESP_ERR_INVALID_RESPONSE;
    }

    *pt_len = data_len;
    ESP_LOGI(TAG, "Decrypted %u bytes", (unsigned)data_len);
    return ESP_OK;
}

esp_err_t ble_crypto_encrypt(const uint8_t *plaintext, size_t pt_len,
                              uint8_t *ciphertext, size_t *ct_len) {
    if (!s_ctx.key_derived) return ESP_ERR_INVALID_STATE;
    if (pt_len > BLE_CRYPTO_MAX_PLAINTEXT) return ESP_ERR_INVALID_SIZE;

    size_t required = BLE_CRYPTO_GCM_IV_LEN + BLE_CRYPTO_GCM_TAG_LEN + pt_len;
    if (*ct_len < required) return ESP_ERR_INVALID_SIZE;

    uint8_t *iv = ciphertext;
    uint8_t *tag = ciphertext + BLE_CRYPTO_GCM_IV_LEN;
    uint8_t *data = ciphertext + BLE_CRYPTO_GCM_IV_LEN + BLE_CRYPTO_GCM_TAG_LEN;

    esp_fill_random(iv, BLE_CRYPTO_GCM_IV_LEN);

    mbedtls_gcm_context gcm;
    mbedtls_gcm_init(&gcm);

    int ret = mbedtls_gcm_setkey(&gcm, MBEDTLS_CIPHER_ID_AES,
                                  s_ctx.shared_key, BLE_CRYPTO_AES_KEY_LEN * 8);
    if (ret != 0) {
        mbedtls_gcm_free(&gcm);
        return ESP_FAIL;
    }

    ret = mbedtls_gcm_crypt_and_tag(&gcm, MBEDTLS_GCM_ENCRYPT, pt_len,
                                     iv, BLE_CRYPTO_GCM_IV_LEN,
                                     NULL, 0,
                                     plaintext, data,
                                     BLE_CRYPTO_GCM_TAG_LEN, tag);
    mbedtls_gcm_free(&gcm);

    if (ret != 0) {
        ESP_LOGE(TAG, "GCM encrypt failed: -0x%04x", -ret);
        return ESP_FAIL;
    }

    *ct_len = required;
    return ESP_OK;
}

void ble_crypto_deinit(void) {
    mbedtls_ecdh_free(&s_ctx.ecdh);
    mbedtls_ctr_drbg_free(&s_ctx.ctr_drbg);
    mbedtls_entropy_free(&s_ctx.entropy);
    memset(&s_ctx, 0, sizeof(s_ctx));
}
