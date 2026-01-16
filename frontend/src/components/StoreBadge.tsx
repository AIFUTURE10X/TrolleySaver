interface StoreBadgeProps {
  store: string;
  size?: 'sm' | 'md' | 'lg';
}

const storeColors: Record<string, { bg: string; text: string }> = {
  woolworths: { bg: 'bg-green-100', text: 'text-green-700' },
  coles: { bg: 'bg-red-100', text: 'text-red-700' },
  aldi: { bg: 'bg-blue-100', text: 'text-blue-700' },
};

const sizes = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
  lg: 'px-3 py-1.5 text-base',
};

export function StoreBadge({ store, size = 'md' }: StoreBadgeProps) {
  const slug = store.toLowerCase();
  const colors = storeColors[slug] || { bg: 'bg-gray-100', text: 'text-gray-700' };

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full ${colors.bg} ${colors.text} ${sizes[size]}`}
    >
      {store}
    </span>
  );
}
