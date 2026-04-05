import StatusBadge from "./StatusBadge";

export default function ConfidenceBadge({ value }: { value: number }) {
  const tone = value >= 0.7 ? "good" : value >= 0.4 ? "warn" : "danger";
  return <StatusBadge label={`${Math.round(value * 100)}% confidence`} tone={tone} />;
}
