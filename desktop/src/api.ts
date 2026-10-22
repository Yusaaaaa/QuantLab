import { invoke, isTauri } from "@tauri-apps/api/core";
export async function command<T = any>(
  name: string,
  args: Record<string, unknown> = {},
): Promise<T> {
  if (isTauri()) return invoke<T>(name, args);
  const response = await fetch("/__quantlab", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-QuantLab-Client": "desktop-dev",
    },
    body: JSON.stringify({ name, args }),
  });
  if (!response.ok)
    throw new Error(
      "无法连接本地引擎。请使用 QuantLab App，或通过 npm run dev 启动开发界面。",
    );
  const payload = await response.json();
  if (payload.error) throw new Error(payload.error);
  return payload.data;
}
export const rpc = (
  root: string,
  action: string,
  args: Record<string, unknown> = {},
) => command("rpc", { root, request: { action, ...args } });
