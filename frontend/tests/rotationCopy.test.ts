import {
  rotationTrailHistoryDisclosure,
  rotationTrailMethodology,
} from "../src/features/sectors/rotationCopy";

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

assert(
  rotationTrailHistoryDisclosure.includes(
    "adjusted sector ETF-versus-SPY history",
  ),
  "trail copy identifies the real ETF history",
);
assert(
  rotationTrailHistoryDisclosure.includes("Relative Trend / Relative Momentum"),
  "trail copy names the canonical indicators",
);
assert(
  rotationTrailMethodology.includes("causally robust-normalized around 100"),
  "methodology explains the normalization center",
);
assert(
  rotationTrailMethodology.includes(
    "Overall rank uses the full sector composite",
  ),
  "methodology does not conflate trails and rank",
);
