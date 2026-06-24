import { useTranslation } from 'react-i18next';

type StatusBadgeProps = {
  value: string | null | undefined;
};

export function StatusBadge({ value }: StatusBadgeProps) {
  const { t } = useTranslation();
  const normalized = value ?? 'unknown';
  return (
    <span className={`status status-${normalized.replaceAll('_', '-')}`}>
      {t(`status.${normalized}`, { defaultValue: normalized })}
    </span>
  );
}
