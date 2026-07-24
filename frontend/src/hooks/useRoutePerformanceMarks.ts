import { useLayoutEffect, useRef } from 'react';

export type RoutePerformanceStage = 'first-analytical-content' | 'decision-ready' | 'route-complete';

export function useRoutePerformanceMarks(
  route: string,
  state: { analytical: boolean; complete: boolean; decisionReady: boolean },
) {
  const marked = useRef(new Set<RoutePerformanceStage>());
  useLayoutEffect(() => {
    markWhenReady(route, 'first-analytical-content', state.analytical, marked.current);
    markWhenReady(route, 'decision-ready', state.decisionReady, marked.current);
    markWhenReady(route, 'route-complete', state.complete, marked.current);
  }, [route, state.analytical, state.complete, state.decisionReady]);
}

function markWhenReady(
  route: string,
  stage: RoutePerformanceStage,
  ready: boolean,
  marked: Set<RoutePerformanceStage>,
) {
  if (!ready || marked.has(stage) || typeof performance === 'undefined' || typeof performance.mark !== 'function') return;
  performance.mark(`market-intelligence:${route}:${stage}`);
  marked.add(stage);
}
