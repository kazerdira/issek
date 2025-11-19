// Enhanced color palette with safe area utilities
export const colors = {
  // Primary colors
  primary: '#6C5CE7',
  primaryDark: '#5F4FCE',
  primaryLight: '#8B7EF2',
  
  // Secondary colors
  secondary: '#00B894',
  secondaryDark: '#00A078',
  
  // Accent
  accent: '#FF6B6B',
  accentLight: '#FF8787',
  
  // Backgrounds
  background: '#FFFFFF',
  backgroundDark: '#0F0F0F',
  surface: '#F8F9FA',
  surfaceDark: '#1A1A1A',
  card: '#FFFFFF',
  cardDark: '#232323',
  
  // Text
  text: '#2D3436',
  textSecondary: '#636E72',
  textLight: '#FFFFFF',
  textDark: '#0F0F0F',
  textMuted: '#95A5A6',
  
  // Status
  success: '#00B894',
  error: '#FF6B6B',
  warning: '#FDCB6E',
  info: '#74B9FF',
  
  // Chat bubbles
  messageSent: '#6C5CE7',
  messageReceived: '#ECEFF1',
  messageSentDark: '#5F4FCE',
  messageReceivedDark: '#2C2C2C',
  
  // Borders
  border: '#DFE6E9',
  borderDark: '#353535',
  
  // Special
  online: '#00B894',
  offline: '#95A5A6',
  typing: '#6C5CE7',
  
  // Transparent
  overlay: 'rgba(0, 0, 0, 0.5)',
  overlayLight: 'rgba(0, 0, 0, 0.3)',
};

// Safe area constants
export const safeArea = {
  // Standard safe area insets
  top: 44, // iPhone notch area
  bottom: 34, // Home indicator area
  tabBar: 60, // Tab bar height
  header: 60, // Header height
};

// Spacing scale
export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
};

// Border radius scale
export const borderRadius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  round: 999,
};

// Typography scale
export const typography = {
  h1: {
    fontSize: 32,
    fontWeight: '700' as '700',
    lineHeight: 40,
  },
  h2: {
    fontSize: 28,
    fontWeight: '700' as '700',
    lineHeight: 36,
  },
  h3: {
    fontSize: 24,
    fontWeight: '600' as '600',
    lineHeight: 32,
  },
  h4: {
    fontSize: 20,
    fontWeight: '600' as '600',
    lineHeight: 28,
  },
  body: {
    fontSize: 16,
    fontWeight: '400' as '400',
    lineHeight: 24,
  },
  bodySmall: {
    fontSize: 14,
    fontWeight: '400' as '400',
    lineHeight: 20,
  },
  caption: {
    fontSize: 12,
    fontWeight: '400' as '400',
    lineHeight: 16,
  },
  button: {
    fontSize: 16,
    fontWeight: '600' as '600',
    lineHeight: 24,
  },
};

// Shadow presets
export const shadows = {
  sm: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  md: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 4,
    elevation: 4,
  },
  lg: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 8,
  },
};
