import { StyleSheet, Text, View } from 'react-native';

import Colors from '@/constants/Colors';
import { useColorScheme } from '@/components/useColorScheme';

export function StatRow({ label, value }: { label: string; value: string }) {
  const scheme = useColorScheme();
  const colors = Colors[scheme];

  return (
    <View style={[styles.row, { borderBottomColor: colors.line }]}>
      <Text style={[styles.label, { color: colors.muted }]}>{label}</Text>
      <Text style={[styles.value, { color: colors.text, fontFamily: 'IBMPlexMono' }]}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  label: {
    fontSize: 15,
  },
  value: {
    fontSize: 16,
  },
});
