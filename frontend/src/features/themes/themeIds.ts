const aliases: Record<string, string> = {
  memory_storage: 'memory_storage',
  'memory-storage': 'memory_storage',
  cybersecurity: 'cybersecurity',
  ai_infrastructure: 'ai_infrastructure',
  'ai-infrastructure': 'ai_infrastructure',
  semiconductors: 'semiconductors',
  cloud_data_centers: 'cloud_data_centers',
  'cloud-data-centers': 'cloud_data_centers',
  defense_aerospace: 'defense_aerospace',
  'defense-aerospace': 'defense_aerospace',
};

export function normalizeThemeId(value: string | null | undefined): string | null {
  if (!value) return null;
  return aliases[value.trim().toLowerCase()] ?? null;
}
