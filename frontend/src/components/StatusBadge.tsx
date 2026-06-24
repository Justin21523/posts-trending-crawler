type StatusBadgeProps = {
  value: string | null | undefined;
};

export function StatusBadge({ value }: StatusBadgeProps) {
  const normalized = value ?? 'unknown';
  return <span className={`status status-${normalized.replaceAll('_', '-')}`}>{normalized}</span>;
}
