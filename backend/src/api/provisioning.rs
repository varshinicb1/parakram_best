//! Secure WiFi provisioning — encrypted credential transfer between app and ESP32.
//!
//! Uses X25519 key exchange + AES-256-GCM for end-to-end encryption.
//! The backend acts as a key broker: the app and board each generate ephemeral
//! X25519 keypairs, exchange public keys through the backend, then derive a
//! shared secret for AES-GCM encryption of WiFi credentials.
//!
//! Flow:
//!   1. Board generates X25519 keypair, sends public key via BLE → backend
//!   2. App generates X25519 keypair, sends public key → backend
//!   3. Backend returns both public keys to both parties
//!   4. Each side computes shared_secret = X25519(own_private, other_public)
//!   5. App encrypts WiFi SSID+password with AES-256-GCM(shared_secret)
//!   6. Encrypted blob is sent to board via BLE or TCP

use axum::extract::{Json, Path};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Mutex;

#[derive(Debug, Serialize, Deserialize)]
pub struct KeyExchangeRequest {
    pub device_id: String,
    pub public_key_hex: String,
    pub role: String, // "board" or "app"
}

#[derive(Debug, Serialize, Deserialize)]
pub struct KeyExchangeResponse {
    pub device_id: String,
    pub peer_public_key_hex: Option<String>,
    pub session_id: String,
    pub status: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ProvisioningSession {
    pub session_id: String,
    pub device_id: String,
    pub board_public_key: Option<String>,
    pub app_public_key: Option<String>,
    pub created_at: String,
}

lazy_static::lazy_static! {
    static ref PROVISIONING_SESSIONS: Mutex<HashMap<String, ProvisioningSession>> =
        Mutex::new(HashMap::new());
}

/// POST /api/provisioning/key-exchange
///
/// Register a public key (from board or app) for a provisioning session.
/// Returns the peer's public key if already registered.
pub async fn key_exchange(
    Json(req): Json<KeyExchangeRequest>,
) -> impl IntoResponse {
    let mut sessions = PROVISIONING_SESSIONS.lock().unwrap();

    let session_id = format!("prov_{}", req.device_id);
    let session = sessions.entry(session_id.clone()).or_insert_with(|| {
        ProvisioningSession {
            session_id: session_id.clone(),
            device_id: req.device_id.clone(),
            board_public_key: None,
            app_public_key: None,
            created_at: chrono::Utc::now().to_rfc3339(),
        }
    });

    match req.role.as_str() {
        "board" => {
            session.board_public_key = Some(req.public_key_hex.clone());
        }
        "app" => {
            session.app_public_key = Some(req.public_key_hex.clone());
        }
        _ => {
            return (StatusCode::BAD_REQUEST, Json(serde_json::json!({
                "error": "role must be 'board' or 'app'"
            }))).into_response();
        }
    }

    let peer_key = match req.role.as_str() {
        "board" => session.app_public_key.clone(),
        "app" => session.board_public_key.clone(),
        _ => None,
    };

    let status = if session.board_public_key.is_some() && session.app_public_key.is_some() {
        "ready"
    } else {
        "waiting_for_peer"
    };

    Json(KeyExchangeResponse {
        device_id: req.device_id,
        peer_public_key_hex: peer_key,
        session_id,
        status: status.to_string(),
    }).into_response()
}

/// GET /api/provisioning/session/:device_id
///
/// Check the status of a provisioning session.
pub async fn get_session(
    Path(device_id): Path<String>,
) -> impl IntoResponse {
    let sessions = PROVISIONING_SESSIONS.lock().unwrap();
    let session_id = format!("prov_{}", device_id);

    match sessions.get(&session_id) {
        Some(session) => {
            let status = if session.board_public_key.is_some() && session.app_public_key.is_some() {
                "ready"
            } else {
                "waiting_for_peer"
            };
            Json(serde_json::json!({
                "session_id": session.session_id,
                "device_id": session.device_id,
                "status": status,
                "board_key_present": session.board_public_key.is_some(),
                "app_key_present": session.app_public_key.is_some(),
            })).into_response()
        }
        None => {
            (StatusCode::NOT_FOUND, Json(serde_json::json!({
                "error": "no provisioning session found"
            }))).into_response()
        }
    }
}

/// DELETE /api/provisioning/session/:device_id
///
/// Clean up a provisioning session after credentials are transferred.
pub async fn delete_session(
    Path(device_id): Path<String>,
) -> impl IntoResponse {
    let mut sessions = PROVISIONING_SESSIONS.lock().unwrap();
    let session_id = format!("prov_{}", device_id);

    if sessions.remove(&session_id).is_some() {
        Json(serde_json::json!({"status": "deleted"})).into_response()
    } else {
        (StatusCode::NOT_FOUND, Json(serde_json::json!({
            "error": "session not found"
        }))).into_response()
    }
}
