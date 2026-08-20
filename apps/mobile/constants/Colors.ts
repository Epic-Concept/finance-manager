const palette = {
  paper: '#f6f7f4',
  ink: '#19211e',
  muted: '#6c736e',
  line: '#e3e6e0',
  verdigris: '#2e6e5e',
  ochre: '#b07d2a',
  clay: '#9a4b3b',
  card: '#ffffff',
};

export default {
  light: {
    text: palette.ink,
    background: palette.paper,
    tint: palette.verdigris,
    tabIconDefault: palette.muted,
    tabIconSelected: palette.verdigris,
    muted: palette.muted,
    line: palette.line,
    card: palette.card,
    accent: palette.verdigris,
    warn: palette.ochre,
    danger: palette.clay,
  },
  dark: {
    text: '#e8ebe6',
    background: '#121613',
    tint: '#6fb39f',
    tabIconDefault: '#8a918c',
    tabIconSelected: '#6fb39f',
    muted: '#8a918c',
    line: '#2a302c',
    card: '#1b211d',
    accent: '#6fb39f',
    warn: '#d4a45a',
    danger: '#c77868',
  },
};
