import StatusBadge from "./StatusBadge";

interface HallucinationGuardProps {
  coverage: number;
  oldestAge: number;
  maxAge?: number;
}

export default function HallucinationGuard({
  coverage,
  oldestAge,
  maxAge = 60,
}: HallucinationGuardProps) {
  if (coverage <= 0) {
    return <StatusBadge label="No data fetched. Trade blocked automatically." tone="danger" />;
  }
  if (coverage < 0.5) {
    return <StatusBadge label="Less than 50% of data was available" tone="warn" />;
  }
  if (oldestAge > maxAge) {
    return <StatusBadge label={`Data is ${Math.round(oldestAge)} min old`} tone="warn" />;
  }
  return <StatusBadge label="Grounded coverage looks healthy" tone="good" />;
}
