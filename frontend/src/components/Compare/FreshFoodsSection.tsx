/**
 * FreshFoodsSection - Display fresh produce and meat prices
 *
 * Shows everyday prices (not just specials) for staple items
 * like fruit, vegetables, and meat across all stores.
 */
import { useState, memo } from 'react';
import { useFreshFoods } from '../../api/hooks';
import type { FreshFoodItem, FreshFoodStorePrice } from '../../types';

const STORE_COLORS: Record<string, string> = {
  woolworths: 'bg-[#00A651]',
  coles: 'bg-[#E01A22]',
  aldi: 'bg-[#00448C]',
  iga: 'bg-[#FF6B00]',
};

const STORE_TEXT_COLORS: Record<string, string> = {
  woolworths: 'text-[#00A651]',
  coles: 'text-[#E01A22]',
  aldi: 'text-[#00448C]',
  iga: 'text-[#FF6B00]',
};

// Individual fresh food card
const FreshFoodCard = memo(function FreshFoodCard({
  item,
}: {
  item: FreshFoodItem;
}) {
  const cheapestPrice = item.stores.length > 0
    ? Math.min(...item.stores.map(s => parseFloat(s.price)))
    : null;

  return (
    <div className="bg-white rounded-xl border shadow-sm hover:shadow-md transition-shadow overflow-hidden">
      {/* Product image */}
      {item.stores[0]?.image_url && (
        <div className="aspect-square bg-gray-50 flex items-center justify-center p-2">
          <img
            src={item.stores[0].image_url}
            alt={item.product_name}
            className="max-h-full max-w-full object-contain"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
        </div>
      )}

      <div className="p-3">
        {/* Product name */}
        <h3 className="font-medium text-gray-900 text-sm line-clamp-2 mb-2">
          {item.product_name}
        </h3>

        {/* Size if available */}
        {item.size && (
          <p className="text-xs text-gray-500 mb-2">{item.size}</p>
        )}

        {/* Store prices */}
        <div className="space-y-1">
          {item.stores.slice(0, 3).map((store) => {
            const price = parseFloat(store.price);
            const isCheapest = price === cheapestPrice && item.stores.length > 1;

            return (
              <div
                key={store.store_id}
                className={`flex items-center justify-between text-xs rounded px-2 py-1 ${
                  isCheapest ? 'bg-green-50' : 'bg-gray-50'
                }`}
              >
                <span
                  className={`font-medium ${
                    STORE_TEXT_COLORS[store.store_slug] || 'text-gray-700'
                  }`}
                >
                  {store.store_name}
                </span>
                <span
                  className={`font-bold ${
                    isCheapest ? 'text-green-600' : 'text-gray-900'
                  }`}
                >
                  ${price.toFixed(2)}
                  {isCheapest && (
                    <span className="ml-1 text-[10px] text-green-600">BEST</span>
                  )}
                </span>
              </div>
            );
          })}
          {item.stores.length > 3 && (
            <p className="text-[10px] text-gray-400 text-center">
              +{item.stores.length - 3} more stores
            </p>
          )}
        </div>

        {/* Price range */}
        {item.price_range && (
          <p className="text-[10px] text-gray-400 mt-2 text-center">
            {item.price_range}
          </p>
        )}
      </div>
    </div>
  );
});

// Category section (produce or meat)
const CategorySection = memo(function CategorySection({
  title,
  icon,
  items,
  bgColor,
}: {
  title: string;
  icon: string;
  items: FreshFoodItem[];
  bgColor: string;
}) {
  const [expanded, setExpanded] = useState(true);

  if (items.length === 0) {
    return null;
  }

  return (
    <div className="mb-6">
      {/* Section header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className={`w-full flex items-center justify-between ${bgColor} rounded-xl p-4 mb-4 text-white hover:opacity-95 transition-opacity`}
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl">{icon}</span>
          <div className="text-left">
            <h2 className="font-bold text-lg">{title}</h2>
            <p className="text-sm opacity-90">{items.length} products</p>
          </div>
        </div>
        <svg
          className={`w-6 h-6 transition-transform ${expanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Products grid */}
      {expanded && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {items.map((item) => (
            <FreshFoodCard key={item.product_id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
});

// Loading skeleton
function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      {/* Produce section skeleton */}
      <div className="bg-gradient-to-r from-green-500 to-emerald-600 rounded-xl p-4 animate-pulse">
        <div className="h-6 w-48 bg-white/30 rounded" />
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="bg-white rounded-xl border shadow-sm overflow-hidden animate-pulse">
            <div className="aspect-square bg-gray-200" />
            <div className="p-3 space-y-2">
              <div className="h-4 bg-gray-200 rounded w-3/4" />
              <div className="h-3 bg-gray-200 rounded w-1/2" />
              <div className="h-6 bg-gray-100 rounded" />
              <div className="h-6 bg-gray-100 rounded" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Empty state
function EmptyState() {
  return (
    <div className="text-center py-12 bg-gray-50 rounded-xl">
      <div className="text-5xl mb-4">🥬🥩</div>
      <h3 className="text-lg font-medium text-gray-900 mb-2">
        No Fresh Foods Data Yet
      </h3>
      <p className="text-gray-500 max-w-md mx-auto">
        Fresh produce and meat prices will appear here once data is imported.
        Check back soon!
      </p>
    </div>
  );
}

export function FreshFoodsSection() {
  const { data, isLoading, error } = useFreshFoods(30);

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  if (error) {
    return (
      <div className="text-center py-8 bg-red-50 rounded-xl">
        <div className="text-4xl mb-4">❌</div>
        <p className="text-red-600">Failed to load fresh foods prices</p>
      </div>
    );
  }

  if (!data || (data.produce.length === 0 && data.meat.length === 0)) {
    return <EmptyState />;
  }

  return (
    <div className="space-y-6">
      {/* Fresh Produce Section */}
      <CategorySection
        title="Fresh Produce"
        icon="🥬"
        items={data.produce}
        bgColor="bg-gradient-to-r from-green-500 to-emerald-600"
      />

      {/* Meat & Seafood Section */}
      <CategorySection
        title="Meat & Seafood"
        icon="🥩"
        items={data.meat}
        bgColor="bg-gradient-to-r from-red-500 to-rose-600"
      />

      {/* Summary */}
      {data.total_products > 0 && (
        <div className="text-center text-sm text-gray-500">
          Showing {data.total_products} products with everyday prices
        </div>
      )}
    </div>
  );
}
