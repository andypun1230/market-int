export function formatThemeTaxonomyLabel(value: string) {
  return value.replace(/[-_]+/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function formatThemeRole(value: string) {
  return formatThemeTaxonomyLabel(value);
}
