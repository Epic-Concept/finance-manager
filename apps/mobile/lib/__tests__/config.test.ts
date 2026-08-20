import AsyncStorage from '@react-native-async-storage/async-storage';

import {
  DEFAULT_API_BASE_URL,
  getApiBaseUrl,
  resetApiBaseUrlCache,
  setApiBaseUrl,
} from '../config';

jest.mock('@react-native-async-storage/async-storage', () =>
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  require('@react-native-async-storage/async-storage/jest/async-storage-mock')
);

describe('config', () => {
  beforeEach(async () => {
    resetApiBaseUrlCache();
    await AsyncStorage.clear();
  });

  it('defaults to the household API host', async () => {
    await expect(getApiBaseUrl()).resolves.toBe(DEFAULT_API_BASE_URL);
  });

  it('persists a custom base URL without trailing slash', async () => {
    await expect(setApiBaseUrl('http://192.168.1.20:8000/')).resolves.toBe(
      'http://192.168.1.20:8000'
    );
    resetApiBaseUrlCache();
    await expect(getApiBaseUrl()).resolves.toBe('http://192.168.1.20:8000');
  });

  it('rejects an empty URL', async () => {
    await expect(setApiBaseUrl('   ')).rejects.toThrow(/cannot be empty/i);
  });
});
