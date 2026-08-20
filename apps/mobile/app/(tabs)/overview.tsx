import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { StatRow } from '@/components/StatRow';
import Colors from '@/constants/Colors';
import { useColorScheme } from '@/components/useColorScheme';
import { formatPercent, getStats, listRules, type Rule, type Stats } from '@/lib/api';

export default function OverviewScreen() {
  const scheme = useColorScheme();
  const colors = Colors[scheme];
  const [stats, setStats] = useState<Stats | null>(null);
  const [rules, setRules] = useState<Rule[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [s, r] = await Promise.all([getStats(), listRules()]);
      setStats(s);
      setRules(r.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load overview');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <ScrollView
      contentContainerStyle={[styles.content, { backgroundColor: colors.background }]}
      refreshControl={
        <RefreshControl refreshing={loading} onRefresh={() => void load()} tintColor={colors.accent} />
      }
    >
      <Text style={[styles.brand, { color: colors.text, fontFamily: 'Newsreader_500Medium' }]}>
        Overview
      </Text>
      <Text style={[styles.subtitle, { color: colors.muted }]}>
        Coverage and active CEL rules at a glance.
      </Text>

      {error ? <Text style={[styles.message, { color: colors.danger }]}>{error}</Text> : null}
      {loading && !stats ? <ActivityIndicator color={colors.accent} style={{ marginTop: 32 }} /> : null}

      {stats ? (
        <View style={[styles.card, { backgroundColor: colors.card, borderColor: colors.line }]}>
          <StatRow label="Coverage" value={formatPercent(stats.coverage)} />
          <StatRow label="Auto-apply rate" value={formatPercent(stats.auto_apply_rate)} />
          <StatRow label="Pending review" value={String(stats.pending_review)} />
          <StatRow label="Cohort depth" value={String(stats.pending_cohorts)} />
          <StatRow label="Transactions" value={String(stats.total_transactions)} />
        </View>
      ) : null}

      {rules.length > 0 ? (
        <View style={{ gap: 8, marginTop: 8 }}>
          <Text style={[styles.section, { color: colors.text, fontFamily: 'Newsreader_500Medium' }]}>
            Rules
          </Text>
          {rules.map((rule) => (
            <View
              key={rule.id}
              style={[styles.rule, { backgroundColor: colors.card, borderColor: colors.line }]}
            >
              <Text style={[styles.ruleExpr, { color: colors.text, fontFamily: 'IBMPlexMono' }]}>
                {rule.expression}
              </Text>
              <Text style={[styles.ruleMeta, { color: colors.muted }]}>
                category {rule.category_id} · priority {rule.priority}
              </Text>
            </View>
          ))}
        </View>
      ) : null}

      {!loading && stats && rules.length === 0 ? (
        <Text style={[styles.message, { color: colors.muted }]}>No active rules yet.</Text>
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
    marginTop: 16,
  },
  card: {
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingTop: 4,
    paddingBottom: 4,
  },
  section: {
    fontSize: 22,
    marginTop: 8,
  },
  rule: {
    borderWidth: 1,
    borderRadius: 8,
    padding: 14,
    gap: 6,
  },
  ruleExpr: {
    fontSize: 13,
    lineHeight: 18,
  },
  ruleMeta: {
    fontSize: 12,
  },
});
