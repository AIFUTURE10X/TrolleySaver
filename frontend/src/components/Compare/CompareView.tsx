/**
 * CompareView - Modal/panel for comparing products across stores
 *
 * Shows both:
 * 1. Brand comparison - Same product at different stores
 * 2. Type comparison - Different brands of same product type
 */
import { useState, memo } from 'react';
import { useTypeMatch, useBrandProducts } from '../../api/hooks';
import type { Special, SpecialStorePrice, TypeMatchResult, BrandProductsResult } from '../../types';

const STORE_COLORS: Record<string, string> = {
  woolworths: 'bg-[#00A651]',
  coles: 'bg-[#E01A22]',
  aldi: 'bg-[#00448C]',
  iga: 'bg-[#FF6B00]',
};

interface CompareViewProps {
  special: Special;
  onClose: () => void;
}

// Toggle between Brand and Type comparison
const CompareToggle = memo(function CompareToggle({
  mode,
  onToggle,
}: {
  mode: 'brand' | 'type';
  onToggle: (mode: 'brand' | 'type') => void;
}) {
  return (
    <div className="flex bg-gray-100 rounded-lg p-1">
      <button
        onClick={() => onToggle('type')}
        className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-all ${
          mode === 'type'
            ? 'bg-white text-blue-600 shadow'
            : 'text-gray-600 hover:text-gray-900'
        }`}
      >
        Compare Product Types
      </button>
      <button
        onClick={() => onToggle('brand')}
        className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-all ${
          mode === 'brand'
            ? 'bg-white text-blue-600 shadow'
            : 'text-gray-600 hover:text-gray-900'
        }`}
      >
        Same Brand Across Stores
      </button>
    </div>
  );
});

// Price comparison row
const PriceRow = memo(function PriceRow({
  item,
  isCheapest,
  isReference,
}: {
  item: SpecialStorePrice;
  isCheapest: boolean;
  isReference?: boolean;
}) {
  return (
    <div
      className={`flex items-center gap-4 p-3 rounded-lg ${
        isCheapest ? 'bg-green-50 border border-green-200' : 'bg-gray-50'
      } ${isReference ? 'ring-2 ring-blue-400' : ''}`}
    >
      {/* Store badge */}
      <span
        className={`${
          STORE_COLORS[item.store_slug] || 'bg-gray-500'
        } text-white text-xs font-medium px-2 py-1 rounded`}
      >
        {item.store_name}
      </span>

      {/* Product image */}
      {item.image_url && (
        <img
          src={item.image_url}
          alt=""
          className="w-12 h-12 object-contain rounded"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = 'none';
          }}
        />
      )}

      {/* Price */}
      <div className="flex-1">
        <div className="flex items-baseline gap-2">
          <span className={`text-lg font-bold ${isCheapest ? 'text-green-600' : 'text-gray-900'}`}>
            {item.price}
          </span>
          {item.was_price && (
            <span className="text-sm text-gray-400 line-through">{item.was_price}</span>
          )}
        </div>
        {item.unit_price && (
          <span className="text-xs text-gray-500">{item.unit_price}</span>
        )}
      </div>

      {/* Discount badge */}
      {item.discount_percent && item.discount_percent > 0 && (
        <span
          className={`text-xs font-bold px-2 py-1 rounded-full ${
            item.discount_percent >= 50
              ? 'bg-red-100 text-red-600'
              : 'bg-orange-100 text-orange-600'
          }`}
        >
          {item.discount_percent}% OFF
        </span>
      )}

      {/* Cheapest badge */}
      {isCheapest && (
        <span className="bg-green-500 text-white text-xs font-bold px-2 py-1 rounded-full">
          CHEAPEST
        </span>
      )}

      {/* Reference badge */}
      {isReference && (
        <span className="bg-blue-500 text-white text-xs font-bold px-2 py-1 rounded-full">
          SELECTED
        </span>
      )}

      {/* View link */}
      {item.product_url && (
        <a
          href={item.product_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:text-blue-800 text-sm"
        >
          View
        </a>
      )}
    </div>
  );
});

// Type comparison view
function TypeComparisonView({ data }: { data: TypeMatchResult }) {
  const allProducts = [data.reference_product, ...data.similar_products];
  const cheapestPrice = Math.min(
    ...allProducts.map((p) => parseFloat(p.price.replace('$', '')))
  );

  return (
    <div className="space-y-4">
      <div className="text-sm text-gray-500">
        Comparing <strong>{data.product_type}</strong>
        {data.category_name && ` in ${data.category_name}`}
      </div>

      <div className="space-y-2">
        {/* Reference product first */}
        <PriceRow
          item={data.reference_product}
          isCheapest={parseFloat(data.reference_product.price.replace('$', '')) === cheapestPrice}
          isReference
        />

        {/* Similar products sorted by price */}
        {data.similar_products.map((product) => (
          <PriceRow
            key={product.special_id}
            item={product}
            isCheapest={parseFloat(product.price.replace('$', '')) === cheapestPrice}
          />
        ))}
      </div>

      {/* Summary */}
      <div className="bg-blue-50 rounded-lg p-4 text-sm">
        <div className="font-medium text-blue-900">
          {data.total_options} options found
        </div>
        {data.cheapest_price && (
          <div className="text-blue-700">
            Cheapest: <strong>{data.cheapest_price}</strong>
          </div>
        )}
      </div>
    </div>
  );
}

// Brand comparison - ALL products from same brand across stores
function BrandComparisonView({
  special,
  data,
  isLoading,
  error,
}: {
  special: Special;
  data: BrandProductsResult | undefined;
  isLoading: boolean;
  error: Error | null;
}) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8 text-red-500">
        <div className="text-4xl mb-4">X</div>
        <p>Failed to load brand comparison data</p>
      </div>
    );
  }

  if (!data || data.brand === 'Unknown') {
    return (
      <div className="text-center py-8 text-gray-500">
        <div className="text-4xl mb-4">?</div>
        <p className="font-medium">No brand information available.</p>
        <p className="text-sm mt-2">
          Try the "Compare Product Types" tab to see similar products.
        </p>
      </div>
    );
  }

  // No other brand products found
  if (data.brand_products.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <div className="text-4xl mb-4">1</div>
        <p className="font-medium">Only {data.brand} product on special</p>
        <p className="text-sm mt-2">
          This is the only {data.brand} product currently on special.
        </p>
        <p className="text-xs mt-4 text-gray-400">
          Try the "Compare Product Types" tab to see similar products from different brands.
        </p>
      </div>
    );
  }

  // All products (reference + others), sorted by price
  const allProducts = [data.reference_product, ...data.brand_products]
    .sort((a, b) => parseFloat(a.price) - parseFloat(b.price));

  const cheapestPrice = parseFloat(data.cheapest_price || allProducts[0].price);

  return (
    <div className="space-y-4">
      {/* Brand header */}
      <div className="bg-blue-50 rounded-lg p-3">
        <div className="text-sm font-medium text-blue-900">
          All <strong>{data.brand}</strong> products on special
        </div>
        <div className="text-xs text-blue-700 mt-1">
          {data.total_products} products across {data.stores_with_brand.length} stores: {data.stores_with_brand.join(', ')}
        </div>
      </div>

      {/* Products list */}
      <div className="space-y-2 max-h-[40vh] overflow-y-auto">
        {allProducts.map((product) => {
          const price = parseFloat(product.price);
          const isCheapest = price === cheapestPrice;
          const isReference = product.special_id === data.reference_product.special_id;

          return (
            <PriceRow
              key={product.special_id}
              item={product}
              isCheapest={isCheapest}
              isReference={isReference}
            />
          );
        })}
      </div>

      {/* Summary */}
      <div className="bg-green-50 rounded-lg p-3 text-sm">
        <div className="font-medium text-green-900">
          {data.total_products} {data.brand} products on special
        </div>
        <div className="text-green-700 mt-1">
          Cheapest: <strong>${cheapestPrice.toFixed(2)}</strong>
        </div>
      </div>
    </div>
  );
}

export function CompareView({ special, onClose }: CompareViewProps) {
  const [mode, setMode] = useState<'brand' | 'type'>('type');

  // Type comparison hook
  const { data: typeData, isLoading: typeLoading, error: typeError } = useTypeMatch(special.id);

  // Brand comparison hook - fetch all products from same brand
  const {
    data: brandData,
    isLoading: brandLoading,
    error: brandError
  } = useBrandProducts(mode === 'brand' ? special.id : 0);

  // Use the appropriate loading/error states based on mode
  const isLoading = mode === 'type' ? typeLoading : brandLoading;
  const error = mode === 'type' ? typeError : brandError;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-lg font-bold text-gray-900">Compare Prices</h2>
              <p className="text-sm text-gray-500 mt-1">{special.name}</p>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Toggle */}
          <div className="mt-4">
            <CompareToggle mode={mode} onToggle={setMode} />
          </div>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[60vh]">
          {mode === 'type' ? (
            isLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
              </div>
            ) : error ? (
              <div className="text-center py-8 text-red-500">
                Failed to load comparison data
              </div>
            ) : typeData ? (
              <TypeComparisonView data={typeData} />
            ) : (
              <div className="text-center py-8 text-gray-500">
                No similar products found
              </div>
            )
          ) : (
            <BrandComparisonView
              special={special}
              data={brandData}
              isLoading={brandLoading}
              error={brandError}
            />
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t bg-gray-50">
          <button
            onClick={onClose}
            className="w-full py-2 px-4 bg-gray-200 text-gray-700 font-medium rounded-lg hover:bg-gray-300 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
