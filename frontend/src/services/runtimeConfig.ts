export function areTestScenariosEnabled(): boolean {
  return stringFlag(process.env.EXPO_PUBLIC_ENABLE_TEST_SCENARIOS)
    || stringFlag(process.env.APP_ENABLE_TEST_SCENARIOS);
}

function stringFlag(value: string | undefined): boolean {
  return value?.trim().toLowerCase() === 'true';
}
