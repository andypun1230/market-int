import { useRouter } from 'expo-router';

import { AppScreen } from '@/components/ui/AppScreen';
import { EmptyState } from '@/components/ui/EmptyState';

export default function UnmatchedRouteScreen() {
  const router = useRouter();
  return (
    <AppScreen
      showBackButton
      subtitle="The requested destination is unavailable."
      title="Page not found"
      widthPolicy="constrained_settings">
      <EmptyState
        actionLabel="Return Home"
        message="The link may be outdated or the address may be incomplete. Return to the application home screen to continue."
        onAction={() => router.replace('/')}
        stateType="unavailable"
        title="This destination was not found"
      />
    </AppScreen>
  );
}
