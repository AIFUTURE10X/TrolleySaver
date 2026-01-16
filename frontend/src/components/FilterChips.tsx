/**
 * FilterChips - Quick discount filter buttons
 * Categories are handled by CategoryTabs component
 */
import { memo } from 'react';

interface FilterChipsProps {
  minDiscount: number;
  onDiscountSelect: (discount: number) => void;
}

// Discount filter chip
const DiscountChip = memo(function DiscountChip({
  label,
  isSelected,
  onClick,
  color = 'red',
}: {
  label: string;
  isSelected: boolean;
  onClick: () => void;
  color?: 'red' | 'orange' | 'yellow';
}) {
  const colorClasses = {
    red: isSelected ? 'bg-red-500 text-white' : 'bg-red-50 text-red-600 hover:bg-red-100',
    orange: isSelected ? 'bg-orange-500 text-white' : 'bg-orange-50 text-orange-600 hover:bg-orange-100',
    yellow: isSelected ? 'bg-yellow-500 text-white' : 'bg-yellow-50 text-yellow-600 hover:bg-yellow-100',
  };

  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${colorClasses[color]}`}
    >
      {label}
    </button>
  );
});

export function FilterChips({
  minDiscount,
  onDiscountSelect,
}: FilterChipsProps) {
  return (
    <div className="flex flex-wrap gap-2 items-center py-2">
      {/* Discount filters */}
      <span className="text-xs text-gray-500 uppercase tracking-wide font-medium">Discount:</span>
      <DiscountChip
        label="50%+ Off"
        isSelected={minDiscount === 50}
        onClick={() => onDiscountSelect(minDiscount === 50 ? 0 : 50)}
        color="red"
      />
      <DiscountChip
        label="25%+ Off"
        isSelected={minDiscount === 25}
        onClick={() => onDiscountSelect(minDiscount === 25 ? 0 : 25)}
        color="orange"
      />
    </div>
  );
}
