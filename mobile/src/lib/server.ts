// Where the Watch Me server is, and small helpers to talk to it. The server does the listening
// work (speech-to-text, the voiceprint, the agents); the app streams audio and shows the results.
import * as SecureStore from 'expo-secure-store';

const KEY = 'watchme.server';

export async function loadServerUrl(): Promise<string> {
  // A saved address wins; EXPO_PUBLIC_SERVER_URL is a convenience for development builds.
  return (await SecureStore.getItemAsync(KEY)) ?? normalize(process.env.EXPO_PUBLIC_SERVER_URL ?? '');
}

export async function saveServerUrl(url: string): Promise<string> {
  const clean = normalize(url);
  await SecureStore.setItemAsync(KEY, clean);
  return clean;
}

/** "192.168.1.20:8000" or "http://192.168.1.20:8000/" -> "http://192.168.1.20:8000" */
export function normalize(url: string): string {
  let u = url.trim().replace(/\/+$/, '');
  if (u && !/^https?:\/\//.test(u)) u = `http://${u}`;
  return u;
}

export function wsUrl(base: string): string {
  return base.replace(/^http/, 'ws') + '/ws';
}

export class ApiError extends Error {}

async function call<T>(base: string, path: string, init?: RequestInit): Promise<T> {
  if (!base) throw new ApiError('Set the server address in Setup first.');
  const response = await fetch(base + path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(body?.detail ?? `Server answered ${response.status}`);
  return body as T;
}

export const api = {
  get: <T>(base: string, path: string) => call<T>(base, path),
  post: <T>(base: string, path: string, body: unknown) =>
    call<T>(base, path, { method: 'POST', body: JSON.stringify(body) }),
};
