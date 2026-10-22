#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use serde_json::{json, Value};
use std::{
    collections::HashMap,
    fs,
    io::Write,
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::Mutex,
};
use tauri::State;
struct Job {
    child: Child,
    directory: PathBuf,
    cancelled: bool,
}
#[derive(Default)]
struct Jobs(Mutex<HashMap<String, Job>>);
fn python(root: &str) -> Result<Command, String> {
    let root = PathBuf::from(root)
        .canonicalize()
        .map_err(|e| e.to_string())?;
    let interpreter = root.join(".venv/bin/python");
    if !interpreter.is_file() {
        return Err(
            "工作区缺少 .venv/bin/python；请选择已配置 Python 环境的 QuantLab 项目。".into(),
        );
    }
    if !root.join("src/quantlab/desktop_bridge.py").is_file() {
        return Err("工作区缺少桌面桥接模块。".into());
    }
    let mut command = Command::new(interpreter);
    command
        .args(["-u", "-m", "quantlab.desktop_bridge"])
        .arg(&root)
        .current_dir(&root)
        .env("PYTHONPATH", root.join("src"))
        .env("MPLBACKEND", "Agg")
        .stdin(Stdio::piped());
    Ok(command)
}
fn call(root: &str, request: &Value) -> Result<Value, String> {
    let mut child = python(root)?
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| e.to_string())?;
    child
        .stdin
        .take()
        .unwrap()
        .write_all(request.to_string().as_bytes())
        .map_err(|e| e.to_string())?;
    let output = child.wait_with_output().map_err(|e| e.to_string())?;
    let payload: Value = serde_json::from_slice(&output.stdout)
        .map_err(|_| String::from_utf8_lossy(&output.stderr).to_string())?;
    if payload["ok"] == true {
        Ok(payload["data"].clone())
    } else {
        Err(payload["error"]["message"]
            .as_str()
            .unwrap_or("Python error")
            .into())
    }
}
#[tauri::command]
async fn rpc(root: String, request: Value) -> Result<Value, String> {
    let allowed = [
        "catalog", "read", "save", "config", "validate", "history", "result", "report",
    ];
    if !allowed.contains(&request["action"].as_str().unwrap_or("")) {
        return Err("Unsupported command".into());
    }
    tauri::async_runtime::spawn_blocking(move || call(&root, &request))
        .await
        .map_err(|e| e.to_string())?
}
#[tauri::command]
async fn start_run(root: String, config: Value, jobs: State<'_, Jobs>) -> Result<Value, String> {
    let root_clone = root.clone();
    let prepared = tauri::async_runtime::spawn_blocking(move || {
        call(&root_clone, &json!({"action":"prepare","config":config}))
    })
    .await
    .map_err(|e| e.to_string())??;
    let id = prepared["id"].as_str().ok_or("Missing job ID")?.to_string();
    let directory = PathBuf::from(
        prepared["directory"]
            .as_str()
            .ok_or("Missing job directory")?,
    );
    let log = fs::File::create(directory.join("logs.txt")).map_err(|e| e.to_string())?;
    let mut child = python(&root)?
        .stdout(Stdio::from(log.try_clone().map_err(|e| e.to_string())?))
        .stderr(Stdio::from(log))
        .spawn()
        .map_err(|e| e.to_string())?;
    child
        .stdin
        .take()
        .unwrap()
        .write_all(json!({"action":"run","id":id}).to_string().as_bytes())
        .map_err(|e| e.to_string())?;
    jobs.0.lock().unwrap().insert(
        id.clone(),
        Job {
            child,
            directory,
            cancelled: false,
        },
    );
    Ok(json!({"id":id}))
}
#[tauri::command]
fn job_status(id: String, jobs: State<'_, Jobs>) -> Result<Value, String> {
    let mut jobs = jobs.0.lock().unwrap();
    let job = jobs.get_mut(&id).ok_or("Unknown job")?;
    let status = job.child.try_wait().map_err(|e| e.to_string())?;
    let log = fs::read_to_string(job.directory.join("logs.txt")).unwrap_or_default();
    let lines: Vec<_> = log.lines().collect();
    let tail = lines[lines.len().saturating_sub(100)..].join("\n");
    if job.cancelled {
        return Ok(json!({"status":"cancelled","log":tail}));
    }
    if let Ok(text) = fs::read_to_string(job.directory.join("result.json")) {
        let mut result: Value = serde_json::from_str(&text).map_err(|e| e.to_string())?;
        result["log"] = json!(tail);
        return Ok(result);
    }
    Ok(
        json!({"status":if status.is_some() {"failed"} else {"running"}, "log":tail,"error":if status.is_some(){"引擎进程退出，请查看日志"}else{""}}),
    )
}
#[tauri::command]
fn cancel_run(id: String, jobs: State<'_, Jobs>) -> Result<(), String> {
    let mut jobs = jobs.0.lock().unwrap();
    let job = jobs.get_mut(&id).ok_or("Unknown job")?;
    if job.child.try_wait().map_err(|e| e.to_string())?.is_none() {
        job.child.kill().map_err(|e| e.to_string())?;
        job.child.wait().map_err(|e| e.to_string())?;
        job.cancelled = true;
    }
    Ok(())
}
#[tauri::command]
fn default_workspace() -> String {
    if let Ok(root) = std::env::var("QUANTLAB_WORKSPACE") {
        return root;
    }
    if let Ok(current) = std::env::current_dir() {
        for root in current.ancestors() {
            if root.join("src/quantlab").is_dir() {
                return root.to_string_lossy().to_string();
            }
        }
    }
    let home = std::env::var("HOME").unwrap_or_default();
    for suffix in ["ChatGPTWorkSpace/QuantLab", "Documents/ChatGPT/QuantLab"] {
        let root = PathBuf::from(&home).join(suffix);
        if root.join("src/quantlab").is_dir() {
            return root.to_string_lossy().to_string();
        }
    }
    String::new()
}
fn main() {
    tauri::Builder::default()
        .manage(Jobs::default())
        .invoke_handler(tauri::generate_handler![
            rpc,
            start_run,
            job_status,
            cancel_run,
            default_workspace
        ])
        .build(tauri::generate_context!())
        .expect("Failed to build QuantLab")
        .run(|app, event| {
            if matches!(event, tauri::RunEvent::Exit) {
                let jobs = tauri::Manager::state::<Jobs>(app);
                for job in jobs.0.lock().unwrap().values_mut() {
                    if matches!(job.child.try_wait(), Ok(None)) {
                        let _ = job.child.kill();
                        let _ = job.child.wait();
                    }
                }
            }
        });
}
