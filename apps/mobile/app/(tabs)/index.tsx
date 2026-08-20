import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { CohortReviewCard } from '@/components/CohortReviewCard';
import Colors from '@/constants/Colors';
import { useColorScheme } from '@/components/useColorScheme';
import {
  listCohorts,
  resolveCohort,
  type Cohort,
  type ResolveAction,
} from '@/lib/api';

export default function ReviewScreen() {
  const scheme = useColorScheme();
  const colors = Colors[scheme];
  const [cohorts, setCohorts] = useState<Cohort[]>([]);
  const [singletons, setSingletons] = useState<number[]>([]);
  const [index, setIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await listCohorts();
      setCohorts(data.items);
      setSingletons(data.singletons);
      setIndex(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load cohorts');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function onResolve(action: ResolveAction, categoryId: number, expression: string) {
    const current = cohorts[index];
    if (!current) return;
    setBusy(true);
    setError(null);
    try {
      await resolveCohort(current.cohort_id, action, categoryId, expression);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Resolve failed');
    } finally {
      setBusy(false);
    }
  }

  const current = cohorts[index];

  return (
    <ScrollView
      contentContainerStyle={[styles.content, { backgroundColor: colors.background }]}
      refreshControl={
        <RefreshControl refreshing={loading} onRefresh={() => void load()} tintColor={colors.accent} />
      }
    >
      <Text style={[styles.brand, { color: colors.text, fontFamily: 'Newsreader_500Medium' }]}>
        Quiet Ledger
      </Text>
      <Text style={[styles.subtitle, { color: colors.muted }]}>
        Confirm cohort classifications from your phone.
      </Text>

      {error ? <Text style={[styles.message, { color: colors.danger }]}>{error}</Text> : null}

      {loading && !current ? (
        <ActivityIndicator color={colors.accent} style={{ marginTop: 32 }} />
      ) : null}

      {!loading && cohorts.length === 0 && singletons.length > 0 ? (
        <View style={[styles.card, { backgroundColor: colors.card, borderColor: colors.line }]}>
          <Text style={[styles.eyebrow, { color: colors.muted }]}>Review · singleton residual</Text>
          <Text style={[styles.heading, { color: colors.text, fontFamily: 'Newsreader_500Medium' }]}>
            Leftovers
          </Text>
          <Text style={[styles.body, { color: colors.muted }]}>
            {singletons.length} transactions did not form a cohort. Resolve them one at a time from
            the review API when you have a spare minute.
          </Text>
          <Text style={[styles.mono, { color: colors.text, fontFamily: 'IBMPlexMono' }]}>
            {singletons.slice(0, 12).join(', ')}
          </Text>
        </View>
      ) : null}

      {!loading && cohorts.length === 0 && singletons.length === 0 ? (
        <Text style={[styles.message, { color: colors.muted }]}>Queue is clear. Nothing to review.</Text>
      ) : null}

      {current ? (
        <CohortReviewCard
          key={current.cohort_id}
          title="Review"
          index={index}
          total={cohorts.length}
          cohort={current}
          busy={busy}
          onResolve={onResolve}
        />
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: {
    padding: 20,
    paddingBottom: 40,
    gap: 12,
    flexGrow: 1,
  },
  brand: {
    fontSize: 34,
    letterSpacing: -0.5,
  },
  subtitle: {
    fontSize: 15,
    marginBottom: 8,
  },
  message: {
    fontSize: 15,
    marginTop: 24,
  },
  card: {
    borderWidth: 1,
    borderRadius: 8,
    padding: 18,
    gap: 10,
  },
  eyebrow: {
    fontSize: 13,
  },
  heading: {
    fontSize: 26,
  },
  body: {
    fontSize: 15,
    lineHeight: 22,
  },
  mono: {
    fontSize: 13,
  },
});
