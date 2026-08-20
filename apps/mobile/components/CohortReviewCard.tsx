import { useState } from 'react';
import {
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { ActionButton } from '@/components/ActionButton';
import Colors from '@/constants/Colors';
import { useColorScheme } from '@/components/useColorScheme';
import type { Cohort, ResolveAction } from '@/lib/api';

type Props = {
  title: string;
  index: number;
  total: number;
  cohort: Cohort;
  busy?: boolean;
  onResolve: (action: ResolveAction, categoryId: number, expression: string) => Promise<void>;
};

export function CohortReviewCard({
  title,
  index,
  total,
  cohort,
  busy = false,
  onResolve,
}: Props) {
  const scheme = useColorScheme();
  const colors = Colors[scheme];
  const [categoryId, setCategoryId] = useState('1');
  const [expression, setExpression] = useState(cohort.expression);

  async function run(action: ResolveAction) {
    await onResolve(action, Number(categoryId) || 1, expression);
  }

  return (
    <View style={[styles.card, { backgroundColor: colors.card, borderColor: colors.line }]}>
      <Text style={[styles.eyebrow, { color: colors.muted }]}>
        {title} · {index + 1} of {total}
      </Text>
      <Text style={[styles.title, { color: colors.text, fontFamily: 'Newsreader_500Medium' }]}>
        {cohort.cluster_key}
      </Text>
      <Text style={[styles.meta, { color: colors.muted, fontFamily: 'IBMPlexMono' }]}>
        {cohort.size} transactions · {cohort.stage} · {cohort.source}
      </Text>

      <View style={styles.samples}>
        {cohort.sample_descriptions.slice(0, 5).map((sample) => (
          <Text key={sample} style={[styles.sample, { color: colors.muted }]}>
            · {sample}
          </Text>
        ))}
      </View>

      <Text style={[styles.hint, { color: colors.muted }]}>CEL (edit to split / specialize)</Text>
      <TextInput
        accessibilityLabel="CEL expression"
        multiline
        value={expression}
        onChangeText={setExpression}
        style={[
          styles.input,
          styles.textarea,
          {
            color: colors.text,
            borderColor: colors.line,
            backgroundColor: colors.background,
            fontFamily: 'IBMPlexMono',
          },
        ]}
      />

      <Text style={[styles.hint, { color: colors.muted }]}>
        labelled FPs {cohort.labelled_false_positives} · dry-run size {cohort.size}
      </Text>

      <Text style={[styles.hint, { color: colors.muted }]}>Category id</Text>
      <TextInput
        accessibilityLabel="Category id"
        keyboardType="number-pad"
        value={categoryId}
        onChangeText={setCategoryId}
        style={[
          styles.input,
          {
            color: colors.text,
            borderColor: colors.line,
            backgroundColor: colors.background,
            fontFamily: 'IBMPlexMono',
          },
        ]}
      />

      <View style={styles.actions}>
        <ActionButton
          primary
          label="Confirm"
          disabled={busy}
          onPress={() => void run('confirm')}
        />
        <ActionButton
          label="Change"
          disabled={busy}
          onPress={() => void run('change')}
        />
        <ActionButton
          label="Skip"
          disabled={busy}
          onPress={() => void run('skip')}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 8,
    padding: 18,
    gap: 10,
  },
  eyebrow: {
    fontSize: 13,
  },
  title: {
    fontSize: 28,
    letterSpacing: -0.4,
  },
  meta: {
    fontSize: 13,
  },
  samples: {
    gap: 4,
    marginTop: 4,
  },
  sample: {
    fontSize: 14,
    lineHeight: 20,
  },
  hint: {
    fontSize: 12,
    marginTop: 4,
  },
  input: {
    borderWidth: 1,
    borderRadius: 6,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
  },
  textarea: {
    minHeight: 84,
    textAlignVertical: 'top',
  },
  actions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 8,
  },
});
