import { useColorScheme as useColorSchemeCore } from 'react-native';

export function useColorScheme(): 'light' | 'dark' {
  const coreScheme = useColorSchemeCore();
  return coreScheme === 'dark' ? 'dark' : 'light';
}
