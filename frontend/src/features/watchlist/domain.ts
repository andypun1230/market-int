import { normalizeSectorId } from "@/features/sectors/sectorSnapshot";

export type WatchlistItemType = "stock" | "sector" | "theme";
export type BaseWatchlistItem = { addedAt: string; id: string; type: WatchlistItemType };
export type StockWatchlistItem = BaseWatchlistItem & { name?: string; ticker: string; type: "stock" };
export type GroupWatchlistItem = BaseWatchlistItem & { name: string; type: "sector" | "theme" };
export type UnifiedWatchlistItem = StockWatchlistItem | GroupWatchlistItem;
export type NewWatchlistItem = Omit<StockWatchlistItem, "addedAt"> | Omit<GroupWatchlistItem, "addedAt">;

export function buildWatchlistKey(type: WatchlistItemType, id: string) {
  return `${normalizeWatchlistItemType(type)}:${normalizeWatchlistId(type, id)}`;
}

export function normalizeWatchlistItemType(value: unknown): WatchlistItemType {
  if (value === "stocks") return "stock";
  if (value === "sectors" || value === "sectorTheme") return "sector";
  if (["themes", "industry", "industry_group", "industryGroup", "group"].includes(String(value))) return "theme";
  if (value === "stock" || value === "sector" || value === "theme") return value;
  return "stock";
}

export function normalizeWatchlistId(type: WatchlistItemType | unknown, id: string) {
  const normalizedType = normalizeWatchlistItemType(type);
  if (normalizedType === "stock") return id.trim().toUpperCase();
  if (normalizedType === "sector") return normalizeSectorId(id) ?? slug(id);
  return slug(id);
}

export function migrateWatchlistData(rawData: unknown, legacyGroups: unknown = []): UnifiedWatchlistItem[] {
  const migrated: UnifiedWatchlistItem[] = [];
  const append = (item: UnifiedWatchlistItem | null) => { if (item) migrated.push(item); };
  if (Array.isArray(rawData)) rawData.forEach((item) => append(normalizeWatchlistItem(item)));
  else if (rawData && typeof rawData === "object") {
    const value = rawData as { items?: unknown; stocks?: unknown; groups?: unknown };
    for (const group of [value.items, value.stocks, value.groups]) {
      if (Array.isArray(group)) group.forEach((item) => append(normalizeWatchlistItem(item)));
    }
  }
  if (Array.isArray(legacyGroups)) legacyGroups.forEach((item) => append(normalizeWatchlistItem(item)));
  return dedupeWatchlistItems(migrated);
}

export function toggleItemInWatchlist(previous: UnifiedWatchlistItem[], input: NewWatchlistItem) {
  const normalized = normalizeNewWatchlistItem(input);
  const key = buildWatchlistKey(normalized.type, normalized.id);
  if (previous.some((item) => buildWatchlistKey(item.type, item.id) === key)) {
    return previous.filter((item) => buildWatchlistKey(item.type, item.id) !== key);
  }
  return dedupeWatchlistItems([...previous, { ...normalized, addedAt: new Date().toISOString() } as UnifiedWatchlistItem]);
}

export const buildNextWatchlistItems = toggleItemInWatchlist;

export function dedupeWatchlistItems(items: UnifiedWatchlistItem[]) {
  const seen = new Set<string>();
  return items.filter((item) => {
    const key = buildWatchlistKey(item.type, item.id);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function isWatchlistItemInList(items: UnifiedWatchlistItem[], type: WatchlistItemType, id: string) {
  const key = buildWatchlistKey(type, id);
  return items.some((item) => buildWatchlistKey(item.type, item.id) === key);
}

export function normalizeNewWatchlistItem(item: NewWatchlistItem): NewWatchlistItem {
  if (item.type === "stock") {
    const ticker = normalizeWatchlistId("stock", item.ticker);
    return { ...item, id: ticker, ticker };
  }
  return { ...item, id: normalizeWatchlistId(item.type, item.id) };
}

export function toWatchlistTitle(id: string) {
  return id.split("-").filter(Boolean).map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
}

function normalizeWatchlistItem(value: unknown): UnifiedWatchlistItem | null {
  if (!value || typeof value !== "object") return null;
  const item = value as Record<string, unknown>;
  const type = normalizeWatchlistItemType(item.type);
  const addedAt = typeof item.addedAt === "string" ? item.addedAt : new Date().toISOString();
  if (type === "sector" || type === "theme") {
    const rawId = typeof item.id === "string" ? item.id : typeof item.name === "string" ? item.name : null;
    if (!rawId) return null;
    const id = normalizeWatchlistId(type, rawId);
    return { addedAt, id, name: typeof item.name === "string" ? item.name : toWatchlistTitle(id), type };
  }
  const ticker = typeof item.ticker === "string" ? item.ticker : typeof item.symbol === "string" ? item.symbol : null;
  if ((type === "stock" || !item.type) && ticker) {
    const normalizedTicker = normalizeWatchlistId("stock", ticker);
    return { addedAt, id: normalizedTicker, name: typeof item.name === "string" ? item.name : undefined, ticker: normalizedTicker, type: "stock" };
  }
  return null;
}

function slug(value: string) {
  return value.trim().toLowerCase().replace(/&/g, "and").replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}
