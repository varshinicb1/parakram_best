use tauri::Manager;

/// Parakram Desktop — AI Firmware Studio
/// Manages Python backend sidecar lifecycle + Tauri plugins
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // Initialize logging in debug mode
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            // Spawn Python backend sidecar
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                start_backend_sidecar(app_handle).await;
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_backend_status,
            restart_backend
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

/// Spawn the Python FastAPI backend as a sidecar process
async fn start_backend_sidecar(app: tauri::AppHandle) {
    use tauri_plugin_shell::ShellExt;

    // Try sidecar first (bundled), fall back to python command (dev mode)
    let result = app.shell()
        .sidecar("parakram-backend")
        .map(|cmd| cmd.spawn());

    match result {
        Ok(Ok((_rx, _child))) => {
            log::info!("[sidecar] Python backend started as sidecar");
        }
        _ => {
            // Dev mode: try starting backend directly
            log::warn!("[sidecar] Sidecar not found, trying dev mode (python main.py)");
            let _ = app.shell()
                .command("python")
                .args(["main.py"])
                .current_dir("../backend")
                .spawn();
        }
    }
}

#[tauri::command]
async fn get_backend_status() -> Result<String, String> {
    let client = reqwest::Client::new();
    match client.get("http://localhost:8000/api/health")
        .timeout(std::time::Duration::from_secs(2))
        .send()
        .await
    {
        Ok(resp) if resp.status().is_success() => Ok("running".into()),
        _ => Ok("offline".into()),
    }
}

#[tauri::command]
async fn restart_backend(app: tauri::AppHandle) -> Result<String, String> {
    start_backend_sidecar(app).await;
    Ok("restarting".into())
}
