#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use serde::{Deserialize, Serialize};
use tauri::Manager;

#[derive(Debug, Serialize, Deserialize)]
struct DriverInfo {
    name: String,
    display_name: String,
    version: String,
    driver_type: String,
    capabilities: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct GoldenBlock {
    id: String,
    name: String,
    category: String,
    description: String,
}

#[tauri::command]
fn get_backend_url() -> String {
    std::env::var("PARAKRAM_BACKEND_URL").unwrap_or_else(|_| "http://localhost:8400".to_string())
}

#[tauri::command]
fn get_app_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

#[tauri::command]
async fn list_golden_blocks(category: Option<String>) -> Result<Vec<GoldenBlock>, String> {
    let library_path = std::path::Path::new("services/hardware_library");
    let mut blocks = Vec::new();

    if let Ok(entries) = std::fs::read_dir(library_path) {
        for entry in entries.flatten() {
            if !entry.path().is_dir() {
                continue;
            }
            let cat_name = entry.file_name().to_string_lossy().to_string();
            if let Some(ref filter) = category {
                if &cat_name != filter {
                    continue;
                }
            }
            if let Ok(files) = std::fs::read_dir(entry.path()) {
                for file in files.flatten() {
                    if file.path().extension().map_or(false, |e| e == "json") {
                        if let Ok(content) = std::fs::read_to_string(file.path()) {
                            if let Ok(block) = serde_json::from_str::<GoldenBlock>(&content) {
                                blocks.push(block);
                            }
                        }
                    }
                }
            }
        }
    }

    Ok(blocks)
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let window = app.get_window("main").unwrap();
            #[cfg(debug_assertions)]
            window.open_devtools();
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_backend_url,
            get_app_version,
            list_golden_blocks,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
