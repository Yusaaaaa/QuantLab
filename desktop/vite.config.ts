import { defineConfig } from "vite";
import { spawn } from "node:child_process";
import { readFileSync, existsSync, openSync, closeSync } from "node:fs";
import { resolve, join } from "node:path";
// Development-only loopback bridge. Packaged apps use Tauri IPC, without an HTTP server.
export default defineConfig({
  clearScreen: false,
  server: { host: "127.0.0.1", port: 1420, strictPort: true },
  plugins: [
    {
      name: "quantlab-local-development",
      configureServer(server) {
        const jobs = new Map<string, any>();
        const launch = (root: string) => {
          root = resolve(root);
          if (!existsSync(join(root, "src/quantlab/desktop_bridge.py")))
            throw new Error("请选择有效的 QuantLab 工作区");
          return {
            root,
            executable: join(root, ".venv/bin/python"),
            env: {
              ...process.env,
              PYTHONPATH: join(root, "src"),
              MPLBACKEND: "Agg",
            },
          };
        };
        const call = (root: string, request: any): Promise<any> =>
          new Promise((accept, reject) => {
            const p = launch(root);
            const child = spawn(
              p.executable,
              ["-u", "-m", "quantlab.desktop_bridge", p.root],
              { cwd: p.root, env: p.env },
            );
            let out = "",
              err = "";
            child.stdout.on("data", (d) => (out += d));
            child.stderr.on("data", (d) => (err += d));
            child.on("error", reject);
            child.on("close", () => {
              try {
                const r = JSON.parse(out);
                r.ok ? accept(r.data) : reject(new Error(r.error.message));
              } catch (e) {
                reject(new Error(err || String(e)));
              }
            });
            child.stdin.end(JSON.stringify(request));
          });
        server.httpServer?.on("close", () => {
          for (const job of jobs.values())
            if (job.child.exitCode === null) job.child.kill();
        });
        server.middlewares.use("/__quantlab", async (req, res) => {
          res.setHeader("Content-Type", "application/json");
          if (
            req.method !== "POST" ||
            req.headers["x-quantlab-client"] !== "desktop-dev" ||
            !["127.0.0.1:1420", "localhost:1420"].includes(
              req.headers.host || "",
            ) ||
            (req.headers.origin &&
              !["http://127.0.0.1:1420", "http://localhost:1420"].includes(
                req.headers.origin,
              ))
          ) {
            res.statusCode = 403;
            res.end("{}");
            return;
          }
          try {
            let body = "";
            for await (const chunk of req) {
              body += chunk;
              if (body.length > 3_000_000) throw new Error("Request too large");
            }
            const { name, args } = JSON.parse(body);
            let data: any;
            if (name === "default_workspace")
              data =
                process.env.QUANTLAB_WORKSPACE || resolve(process.cwd(), "..");
            else if (name === "rpc") {
              if (
                ![
                  "catalog",
                  "read",
                  "save",
                  "config",
                  "validate",
                  "history",
                  "result",
                  "report",
                ].includes(args.request.action)
              )
                throw new Error("Unknown action");
              data = await call(args.root, args.request);
            } else if (name === "start_run") {
              const prepared = await call(args.root, {
                action: "prepare",
                config: args.config,
              });
              const p = launch(args.root);
              const fd = openSync(join(prepared.directory, "logs.txt"), "a");
              const child = spawn(
                p.executable,
                ["-u", "-m", "quantlab.desktop_bridge", p.root],
                { cwd: p.root, env: p.env, stdio: ["pipe", fd, fd] },
              );
              closeSync(fd);
              child.on("error", (error) => {
                const job = jobs.get(prepared.id);
                if (job) job.error = String(error);
              });
              child.stdin.end(
                JSON.stringify({ action: "run", id: prepared.id }),
              );
              jobs.set(prepared.id, {
                child,
                directory: prepared.directory,
                cancelled: false,
              });
              data = { id: prepared.id };
            } else if (name === "job_status" || name === "cancel_run") {
              const job = jobs.get(args.id);
              if (!job) throw new Error("Unknown job");
              if (name === "cancel_run") {
                if (job.child.exitCode === null) {
                  job.child.kill();
                  job.cancelled = true;
                }
                data = null;
              } else {
                let log = "";
                try {
                  log = readFileSync(join(job.directory, "logs.txt"), "utf8")
                    .split("\n")
                    .slice(-100)
                    .join("\n");
                } catch {}
                const file = join(job.directory, "result.json");
                data = job.cancelled
                  ? { status: "cancelled", log }
                  : existsSync(file)
                    ? { ...JSON.parse(readFileSync(file, "utf8")), log }
                    : {
                        status:
                          job.child.exitCode === null && !job.error
                            ? "running"
                            : "failed",
                        log,
                        error: job.error || "引擎进程退出",
                      };
              }
            } else throw new Error("Unknown command");
            res.end(JSON.stringify({ data }));
          } catch (e) {
            res.end(
              JSON.stringify({
                error: e instanceof Error ? e.message : String(e),
              }),
            );
          }
        });
      },
    },
  ],
});
