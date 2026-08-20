import { api, formatPercent, listCohorts, resolveCohort } from '../api';
import { resetApiBaseUrlCache, setApiBaseUrl } from '../config';

jest.mock('@react-native-async-storage/async-storage', () =>
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  require('@react-native-async-storage/async-storage/jest/async-storage-mock')
);

describe('api', () => {
  beforeEach(async () => {
    resetApiBaseUrlCache();
    await setApiBaseUrl('http://example.test:8000');
    globalThis.fetch = jest.fn() as unknown as typeof fetch;
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  it('formats coverage as a percent', () => {
    expect(formatPercent(0.74)).toBe('74%');
    expect(formatPercent(0)).toBe('0%');
  });

  it('calls the configured base URL', async () => {
    (globalThis.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ items: [], singletons: [1] }),
    });

    await expect(listCohorts()).resolves.toEqual({ items: [], singletons: [1] });
    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://example.test:8000/api/v1/cohorts',
      expect.objectContaining({
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      })
    );
  });

  it('posts cohort resolve payloads', async () => {
    (globalThis.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ cohort_id: 'c1', action: 'confirm', resolved: 3 }),
    });

    await resolveCohort('c1', 'confirm', 4, 'merchant == "X"');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://example.test:8000/api/v1/cohorts/c1/resolve',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          action: 'confirm',
          category_id: 4,
          expression: 'merchant == "X"',
        }),
      })
    );
  });

  it('throws on non-OK responses', async () => {
    (globalThis.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Server Error',
    });

    await expect(api('/boom')).rejects.toThrow('500 Server Error');
  });
});
