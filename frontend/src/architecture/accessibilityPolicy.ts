export const ACCESSIBILITY_POLICY = {
  contrast: {
    largeTextMinimum: 3,
    normalTextMinimum: 4.5,
    nonTextMinimum: 3,
  },
  focus: {
    colorToken: 'focus',
    offset: 2,
    owner: 'global.css focus-visible and AppButton native fallback',
    width: 3,
  },
  smallText: {
    chartExceptions: [8, 9],
    essentialMinimum: 11,
  },
  touch: {
    minimumHeight: 44,
    minimumWidth: 44,
  },
} as const;

export function contrastRatio(foreground: string, background: string) {
  const foregroundLuminance = relativeLuminance(foreground);
  const backgroundLuminance = relativeLuminance(background);
  const lighter = Math.max(foregroundLuminance, backgroundLuminance);
  const darker = Math.min(foregroundLuminance, backgroundLuminance);
  return (lighter + 0.05) / (darker + 0.05);
}

function relativeLuminance(hex: string) {
  const channels = hex.match(/[0-9a-f]{2}/gi);
  if (!channels || channels.length !== 3) return 0;
  const [red, green, blue] = channels.map((channel) => {
    const normalized = Number.parseInt(channel, 16) / 255;
    return normalized <= 0.04045
      ? normalized / 12.92
      : ((normalized + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}
