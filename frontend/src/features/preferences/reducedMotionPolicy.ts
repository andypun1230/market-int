export function resolveReducedMotion(appPreference: boolean, platformPreference: boolean) {
  return appPreference || platformPreference;
}
