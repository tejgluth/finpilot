import StatusBadge from "./StatusBadge";

export default function DataFreshnessTag({ minutes }: { minutes: number }) {
  const tone = minutes <= 60 ? "good" : minutes <= 120 ? "warn" : "danger";
  return <StatusBadge label={`${Math.round(minutes)} min old`} tone={tone} />;
}
