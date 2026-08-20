import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY = 'quiet_ledger.apiBaseUrl';

/** Default points at the household host used by Quiet Ledger. */
export const DEFAULT_API_BASE_URL = 'http://gb10.local:8000';

let cachedBaseUrl: string | null = null;

export async function getApiBaseUrl(): Promise<string> {
  if (cachedBaseUrl) return cachedBaseUrl;
  const stored = await AsyncStorage.getItem(STORAGE_KEY);
  cachedBaseUrl = (stored?.trim() || DEFAULT_API_BASE_URL).replace(/\/$/, '');
  return cachedBaseUrl;
}

export async function setApiBaseUrl(url: string): Promise<string> {
  const normalized = url.trim().replace(/\/$/, '');
  if (!normalized) {
    throw new Error('API base URL cannot be empty');
  }
  await AsyncStorage.setItem(STORAGE_KEY, normalized);
  cachedBaseUrl = normalized;
  return normalized;
}

/** Test helper — clears in-memory cache between cases. */
export function resetApiBaseUrlCache(): void {
  cachedBaseUrl = null;
}
