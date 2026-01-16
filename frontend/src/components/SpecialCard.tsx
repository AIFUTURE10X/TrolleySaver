import { StoreBadge } from './StoreBadge';
import type { Special } from '../types';

interface SpecialCardProps {
  special: Special;
}

const STORE_COLORS: Record<string, { bg: string; text: string; badge: string }> = {
  woolworths: { bg: 'bg-[#00A651]/5', text: 'text-[#00A651]', badge: 'bg-[#00A651]' },
  coles: { bg: 'bg-[#E01A22]/5', text: 'text-[#E01A22]', badge: 'bg-[#E01A22]' },
  aldi: { bg: 'bg-[#00448C]/5', text: 'text-[#00448C]', badge: 'bg-[#00448C]' },
};

export function SpecialCard({ special }: SpecialCardProps) {
  const storeSlug = special.store_slug || 'woolworths';
  const colors = STORE_COLORS[storeSlug] || STORE_COLORS.woolworths;

  return (
    <div className={`relative bg-white rounded-xl shadow-sm border hover:shadow-md transition-all overflow-hidden ${colors.bg}`}>
      {/* Discount Badge - Top Right Corner */}
      {special.discount_percent && special.discount_percent > 0 && (
        <div className="absolute top-2 right-2 z-10">
          <span className={`${special.discount_percent >= 50 ? 'bg-red-500' : 'bg-yellow-500'} text-white text-xs font-bold px-2 py-1 rounded-full shadow`}>
            {special.discount_percent}% OFF
          </span>
        </div>
      )}

      <div className="relative">
        {/* Product Image */}
        <div className="aspect-square bg-white p-4 flex items-center justify-center">
          <img
            src={special.image_url || '/placeholder-product.svg'}
            alt={special.name}
            className="max-h-full max-w-full object-contain"
            onError={(e) => {
              (e.target as HTMLImageElement).src = '/placeholder-product.svg';
            }}
          />
        </div>

        {/* Store Badge - Bottom of Image */}
        <div className="absolute bottom-2 left-2">
          <StoreBadge store={special.store_name || storeSlug} size="sm" />
        </div>
      </div>

      {/* Product Details */}
      <div className="p-4 border-t">
        {/* Brand */}
        {special.brand && (
          <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">
            {special.brand}
          </span>
        )}

        {/* Product Name */}
        <h3 className="font-semibold text-gray-900 line-clamp-2 mt-0.5 min-h-[2.5rem]">
          {special.name}
        </h3>

        {/* Size */}
        {special.size && (
          <span className="inline-block mt-1 text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
            {special.size}
          </span>
        )}

        {/* Price Row */}
        <div className="mt-3 flex items-baseline gap-2">
          <span className={`text-2xl font-bold ${colors.text}`}>
            ${special.price}
          </span>
          {special.was_price && (
            <span className="text-sm text-gray-400 line-through">
              ${special.was_price}
            </span>
          )}
        </div>

        {/* Unit Price */}
        {special.unit_price && (
          <div className="text-xs text-gray-500 mt-1">
            {special.unit_price}
          </div>
        )}

        {/* Category */}
        {special.category && (
          <div className="mt-2">
            <span className="text-xs text-gray-400">
              {special.category}
            </span>
          </div>
        )}
      </div>

      {/* View at Store Link */}
      {special.product_url && (
        <div className="px-4 pb-4">
          <a
            href={special.product_url}
            target="_blank"
            rel="noopener noreferrer"
            className={`block w-full text-center text-sm font-medium py-2 rounded-lg ${colors.badge} text-white hover:opacity-90 transition-opacity`}
          >
            View at {special.store_name || storeSlug}
          </a>
        </div>
      )}
    </div>
  );
}
