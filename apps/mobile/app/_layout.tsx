import {
  IBMPlexMono_400Regular,
  useFonts as useMonoFonts,
} from '@expo-google-fonts/ibm-plex-mono';
import {
  Newsreader_500Medium,
  useFonts as useDisplayFonts,
} from '@expo-google-fonts/newsreader';
import { ThemeProvider, DarkTheme, DefaultTheme } from '@react-navigation/native';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect } from 'react';
import 'react-native-reanimated';
import { StatusBar } from 'expo-status-bar';

import { useColorScheme } from '@/components/useColorScheme';
import Colors from '@/constants/Colors';

export { ErrorBoundary } from 'expo-router';

export const unstable_settings = {
  initialRouteName: '(tabs)',
};

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const [displayLoaded, displayError] = useDisplayFonts({
    Newsreader_500Medium,
  });
  const [monoLoaded, monoError] = useMonoFonts({
    IBMPlexMono: IBMPlexMono_400Regular,
  });

  useEffect(() => {
    if (displayError) throw displayError;
    if (monoError) throw monoError;
  }, [displayError, monoError]);

  useEffect(() => {
    if (displayLoaded && monoLoaded) {
      SplashScreen.hideAsync();
    }
  }, [displayLoaded, monoLoaded]);

  if (!displayLoaded || !monoLoaded) {
    return null;
  }

  return <RootLayoutNav />;
}

function RootLayoutNav() {
  const colorScheme = useColorScheme();
  const colors = Colors[colorScheme];

  const theme = {
    ...(colorScheme === 'dark' ? DarkTheme : DefaultTheme),
    colors: {
      ...(colorScheme === 'dark' ? DarkTheme.colors : DefaultTheme.colors),
      primary: colors.tint,
      background: colors.background,
      card: colors.background,
      text: colors.text,
      border: colors.line,
    },
  };

  return (
    <ThemeProvider value={theme}>
      <StatusBar style={colorScheme === 'dark' ? 'light' : 'dark'} />
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      </Stack>
    </ThemeProvider>
  );
}
