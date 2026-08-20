import { getApiBaseUrl } from './config';

export type Cohort = {
  cohort_id: string;
  stage: string;
  cluster_key: string;
  expression: string;
  transaction_ids: number[];
  sample_descriptions: string[];
  labelled_false_positives: number;
  source: string;
  size: number;
};

export type Stats = {
  coverage: number;
  auto_apply_rate: number;
  pending_review: number;
  pending_cohorts: number;
  total_transactions: number;
  decided: number;
  auto_applied: number;
};

export type Rule = {
  id: number;
  name: string;
  expression: string;
  category_id: number;
  priority: number;
};

export type CohortList = {
  items: Cohort[];
  singletons: number[];
};

export type ResolveAction = 'confirm' | 'skip' | 'change';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const base = await getApiBaseUrl();
  const res = await fetch(`${base}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    throw new ApiError(`${res.status} ${res.statusText}`, res.status);
  }
  return res.json() as Promise<T>;
}

export function listCohorts(): Promise<CohortList> {
  return api<CohortList>('/api/v1/cohorts');
}

export function resolveCohort(
  cohortId: string,
  action: ResolveAction,
  categoryId: number,
  expression: string
): Promise<{ cohort_id: string; action: string; resolved: number }> {
  return api(`/api/v1/cohorts/${encodeURIComponent(cohortId)}/resolve`, {
    method: 'POST',
    body: JSON.stringify({
      action,
      category_id: categoryId,
      expression,
    }),
  });
}

export function getStats(): Promise<Stats> {
  return api<Stats>('/api/v1/stats');
}

export function listRules(): Promise<{ items: Rule[] }> {
  return api<{ items: Rule[] }>('/api/v1/rules');
}

export async function pingHealth(): Promise<{ status: string; version?: string }> {
  return api('/health');
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}
