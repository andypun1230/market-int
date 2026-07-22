export function resolveSessionActiveIntent(
  responseIntent?: string | null,
  previousIntent?: string | null,
): string | null {
  const current = responseIntent?.trim() || null;
  const previous = previousIntent?.trim() || null;
  const substantivePrevious = previous && !isFollowUp(previous) ? previous : null;
  if (!current || isFollowUp(current)) return substantivePrevious;
  return current;
}

function isFollowUp(intent: string) {
  return intent.trim().toUpperCase().replaceAll('-', '_') === 'FOLLOW_UP';
}
