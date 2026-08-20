import {
  Pressable,
  StyleSheet,
  Text,
  type PressableProps,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

import Colors from '@/constants/Colors';
import { useColorScheme } from '@/components/useColorScheme';

type Props = PressableProps & {
  label: string;
  primary?: boolean;
  style?: StyleProp<ViewStyle>;
};

export function ActionButton({ label, primary = false, style, disabled, ...rest }: Props) {
  const scheme = useColorScheme();
  const colors = Colors[scheme];

  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled}
      style={({ pressed }) => [
        styles.base,
        {
          backgroundColor: primary ? colors.accent : colors.card,
          borderColor: colors.line,
          opacity: disabled ? 0.45 : pressed ? 0.75 : 1,
        },
        style,
      ]}
      {...rest}
    >
      <Text
        style={[
          styles.label,
          { color: primary ? colors.card : colors.text },
        ]}
      >
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    borderWidth: 1,
    borderRadius: 6,
    paddingVertical: 12,
    paddingHorizontal: 14,
    alignItems: 'center',
    minWidth: 96,
  },
  label: {
    fontSize: 15,
    fontWeight: '600',
  },
});
