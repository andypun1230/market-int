const canonicalIds = [
  'artificial_intelligence', 'semiconductors', 'memory_storage', 'data_centers', 'cloud_computing',
  'enterprise_software', 'cybersecurity', 'networking_infrastructure', 'robotics_automation',
  'digital_advertising', 'ecommerce', 'digital_payments', 'online_travel', 'gaming_interactive_media',
  'streaming_digital_entertainment', 'aerospace_defense', 'space_economy', 'drones_autonomous_systems',
  'nuclear_energy', 'grid_modernization', 'clean_energy', 'electric_vehicles_batteries', 'biotechnology',
  'obesity_metabolic_health', 'medical_technology', 'cryptocurrency_infrastructure',
] as const;

const aliases: Record<string, string> = Object.fromEntries(canonicalIds.flatMap((id) => [[id, id], [id.replaceAll('_', '-'), id]]));

Object.assign(aliases, {
  memory_storage: 'memory_storage',
  'memory-storage': 'memory_storage',
  cybersecurity: 'cybersecurity',
  ai_infrastructure: 'artificial_intelligence',
  'ai-infrastructure': 'artificial_intelligence',
  semiconductors: 'semiconductors',
  cloud_data_centers: 'data_centers',
  'cloud-data-centers': 'data_centers',
  defense_aerospace: 'aerospace_defense',
  'defense-aerospace': 'aerospace_defense',
});

export function normalizeThemeId(value: string | null | undefined): string | null {
  if (!value) return null;
  return aliases[value.trim().toLowerCase()] ?? null;
}
