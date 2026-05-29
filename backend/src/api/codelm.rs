//! CodeLM bridge — proxies requests to the local CodeLM Python service.
//!
//! The CodeLM model runs as a sidecar on port 8401. This module provides
//! `/api/codelm/generate` and `/api/codelm/health` endpoints that the
//! mobile apps and web playground call.

use axum::{extract::State, http::StatusCode, routing::{get, post}, Json, Router};
use serde::{Deserialize, Serialize};
use crate::AppState;
use crate::api::auth::{extract_bearer_token, validate_token, ErrorBody, ErrorDetail};

const CODELM_BASE: &str = "http://127.0.0.1:8401";

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/generate", post(generate))
        .route("/health", get(health))
}

#[derive(Debug, Deserialize)]
pub struct GenerateRequest {
    pub intent: String,
    #[serde(default = "default_mcu")]
    pub target_mcu: String,
}

fn default_mcu() -> String {
    "esp32s3".to_string()
}

#[derive(Debug, Serialize, Deserialize)]
pub struct GenerateResponse {
    pub block_sequence: Vec<String>,
    pub source_code: String,
    pub target_mcu: String,
    pub confidence: f64,
    pub constraint_scores: serde_json::Value,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct CodeLMHealth {
    pub status: String,
    pub model: String,
}

async fn generate(
    State(state): State<AppState>,
    headers: axum::http::HeaderMap,
    Json(req): Json<GenerateRequest>,
) -> Result<Json<GenerateResponse>, (StatusCode, Json<ErrorBody>)> {
    let token = extract_bearer_token(&headers)?;
    let _claims = validate_token(&token, &state)?;

    let client = reqwest::Client::new();
    let resp = client
        .post(format!("{}/api/codelm/generate", CODELM_BASE))
        .json(&serde_json::json!({
            "intent": req.intent,
            "target_mcu": req.target_mcu,
        }))
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| {
            (StatusCode::SERVICE_UNAVAILABLE, Json(ErrorBody {
                error: ErrorDetail {
                    code: "CODELM_UNAVAILABLE".into(),
                    message: format!("CodeLM service not reachable: {}", e),
                },
            }))
        })?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err((
            StatusCode::from_u16(status.as_u16()).unwrap_or(StatusCode::INTERNAL_SERVER_ERROR),
            Json(ErrorBody {
                error: ErrorDetail {
                    code: "CODELM_ERROR".into(),
                    message: body,
                },
            }),
        ));
    }

    let result: GenerateResponse = resp.json().await.map_err(|e| {
        (StatusCode::INTERNAL_SERVER_ERROR, Json(ErrorBody {
            error: ErrorDetail {
                code: "CODELM_PARSE_ERROR".into(),
                message: format!("Failed to parse CodeLM response: {}", e),
            },
        }))
    })?;

    Ok(Json(result))
}

async fn health(
) -> Result<Json<CodeLMHealth>, (StatusCode, Json<ErrorBody>)> {
    let client = reqwest::Client::new();
    let resp = client
        .get(format!("{}/api/codelm/health", CODELM_BASE))
        .timeout(std::time::Duration::from_secs(5))
        .send()
        .await
        .map_err(|_| {
            (StatusCode::SERVICE_UNAVAILABLE, Json(ErrorBody {
                error: ErrorDetail {
                    code: "CODELM_UNAVAILABLE".into(),
                    message: "CodeLM service not reachable".into(),
                },
            }))
        })?;

    let result: CodeLMHealth = resp.json().await.map_err(|e| {
        (StatusCode::INTERNAL_SERVER_ERROR, Json(ErrorBody {
            error: ErrorDetail {
                code: "CODELM_PARSE_ERROR".into(),
                message: format!("Failed to parse CodeLM health: {}", e),
            },
        }))
    })?;

    Ok(Json(result))
}
