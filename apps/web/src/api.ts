const API = '';

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

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
};

export type Rule = {
  id: number;
  name: string;
  expression: string;
  category_id: number;
};
