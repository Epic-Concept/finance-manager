import { useCallback, useEffect, useState } from 'react';
import {
  StyleSheet,
  Text,
  TextInput,
  View,
  ScrollView,
} from 'react-native';

import { ActionButton } from '@/components/ActionButton';
import Colors from '@/constants/Colors';
import { useColorScheme } from '@/components/useColorScheme';
import { pingHealth } from '@/lib/api';
import { DEFAULT_API_BASE_URL, getApiBaseUrl, setApiBaseUrl } from '@/lib/config';

export default function SettingsScreen() {
  const scheme = useColorScheme();
  const colors = Colors[scheme];
  const [url, setUrl] = useState(DEFAULT_API_BASE_URL);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void getApiBaseUrl().then(setUrl);
  }, []);

  const save = useCallback(async () => {
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const saved = await setApiBaseUrl(url);
      setUrl(saved);
      const health = await pingHealth();
      setStatus(`Connected · ${health.status}${health.version ? ` · v${health.version}` : ''}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not reach API');
    } finally {
      setBusy(false);
    }
  }, [url]);

  return (
    <ScrollView contentContainerStyle={[styles.content, { backgroundColor: colors.background }]}>
      <Text style={[styles.brand, { color: colors.text, fontFamily: 'Newsreader_500Medium' }]}>
        Settings
      </Text>
      <Text style={[styles.subtitle, { color: colors.muted }]}>
        Point the app at your Quiet Ledger API. On a physical iPhone, use your LAN hostname or IP —
        localhost will not work.
      </Text>

      <Text style={[styles.label, { color: colors.muted }]}>API base URL</Text>
      <TextInput
        accessibilityLabel="API base URL"
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="url"
        value={url}
        onChangeText={setUrl}
        placeholder={DEFAULT_API_BASE_URL}
        placeholderTextColor={colors.muted}
        style={[
          styles.input,
          {
            color: colors.text,
            borderColor: colors.line,
            backgroundColor: colors.card,
            fontFamily: 'IBMPlexMono',
          },
        ]}
      />

      <View style={styles.actions}>
        <ActionButton primary label={busy ? 'Checking…' : 'Save & check'} disabled={busy} onPress={() => void save()} />
        <ActionButton
          label="Reset default"
          disabled={busy}
          onPress={() => setUrl(DEFAULT_API_BASE_URL)}
        />
      </View>

      {status ? <Text style={[styles.status, { color: colors.accent }]}>{status}</Text> : null}
      {error ? <Text style={[styles.status, { color: colors.danger }]}>{error}</Text> : null}

      <View style={[styles.card, { backgroundColor: colors.card, borderColor: colors.line }]}>
        <Text style={[styles.cardTitle, { color: colors.text, fontFamily: 'Newsreader_500Medium' }]}>
          TestFlight
        </Text>
        <Text style={[styles.body, { color: colors.muted }]}>
          With your Apple Developer account, run `eas build -p ios` then `eas submit -p ios` from
          apps/mobile. Install the build via TestFlight on your phone.
        </Text>
      </View>
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
    lineHeight: 22,
    marginBottom: 8,
  },
  label: {
    fontSize: 12,
  },
  input: {
    borderWidth: 1,
    borderRadius: 6,
    paddingHorizontal: 12,
    paddingVertical: 12,
    fontSize: 14,
  },
  actions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  status: {
    fontSize: 14,
  },
  card: {
    marginTop: 16,
    borderWidth: 1,
    borderRadius: 8,
    padding: 16,
    gap: 8,
  },
  cardTitle: {
    fontSize: 20,
  },
  body: {
    fontSize: 14,
    lineHeight: 21,
  },
});
