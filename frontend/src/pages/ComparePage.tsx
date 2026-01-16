/**
 * ComparePage - Dedicated product comparison search page
 *
 * Features:
 * - Search bar to find any product
 * - Results grouped by product type
 * - All brands within each type with store prices
 */
import { useState, useEffect, memo, useMemo } from 'react';
import { useBrandMatch } from '../api/hooks';
import type { BrandMatchResult, SpecialStorePrice } from '../types';
import { FreshFoodsSection } from '../components/Compare/FreshFoodsSection';

const STORE_COLORS: Record<string, string> = {
  woolworths: 'bg-[#00A651]',
  coles: 'bg-[#E01A22]',
  aldi: 'bg-[#00448C]',
  iga: 'bg-[#FF6B00]',
};

const POPULAR_SEARCHES = ['Milk', 'Bread', 'Butter', 'Chocolate', 'Coca Cola', 'Cheese', 'Chicken'];

// Extract product type from name (remove brand if present)
function extractProductType(name: string, brand: string | null): string {
  if (!brand) return name;
  // Remove brand from start of name
  const brandLower = brand.toLowerCase();
  const nameLower = name.toLowerCase();
  if (nameLower.startsWith(brandLower)) {
    return name.slice(brand.length).trim();
  }
  return name;
}

// Group results by product type
function groupByProductType(results: BrandMatchResult[]): Record<string, BrandMatchResult[]> {
  const groups: Record<string, BrandMatchResult[]> = {};

  for (const result of results) {
    const type = extractProductType(result.product_name, result.brand);
    // Add size to type for better grouping
    const key = result.size ? `${type} (${result.size})` : type;

    if (!groups[key]) {
      groups[key] = [];
    }
    groups[key].push(result);
  }

  // Sort groups by number of options (more options first)
  const sortedKeys = Object.keys(groups).sort(
    (a, b) => groups[b].length - groups[a].length
  );

  const sortedGroups: Record<string, BrandMatchResult[]> = {};
  for (const key of sortedKeys) {
    sortedGroups[key] = groups[key];
  }

  return sortedGroups;
}

// Product card showing brand with store prices
const ProductCompareCard = memo(function ProductCompareCard({
  product,
  onClick,
}: {
  product: BrandMatchResult;
  onClick: () => void;
}) {
  const storeCount = product.stores.length;
  const cheapestStore = product.cheapest_store;

  return (
    <div
      onClick={onClick}
      className="bg-white border rounded-xl p-4 hover:shadow-lg transition-shadow cursor-pointer group"
    >
      {/* Product image and info */}
      <div className="flex items-start gap-3">
        {product.stores[0]?.image_url && (
          <img
            src={product.stores[0].image_url}
            alt=""
            className="w-16 h-16 object-contain rounded bg-gray-50 group-hover:scale-105 transition-transform"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
        )}
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-sm text-gray-900 line-clamp-2">
            {product.product_name}
          </h4>
          {product.brand && (
            <p className="text-xs text-gray-500 mt-0.5">{product.brand}</p>
          )}
          {product.size && (
            <p className="text-xs text-gray-400">{product.size}</p>
          )}
        </div>
      </div>

      {/* Store price badges */}
      <div className="mt-3 flex flex-wrap gap-1">
        {product.stores.slice(0, 4).map((store) => (
          <span
            key={store.special_id}
            className={`${STORE_COLORS[store.store_slug] || 'bg-gray-500'} text-white text-xs px-2 py-1 rounded font-medium`}
          >
            {store.price}
          </span>
        ))}
        {product.stores.length > 4 && (
          <span className="text-xs text-gray-400 px-2 py-1">
            +{product.stores.length - 4} more
          </span>
        )}
      </div>

      {/* Savings indicator */}
      <div className="mt-3 flex justify-between items-center text-xs">
        <span className="text-gray-500">{storeCount} stores</span>
        {product.savings_potential && (
          <span className="text-green-600 font-medium">
            Save up to {product.savings_potential}
          </span>
        )}
      </div>

      {cheapestStore && (
        <div className="mt-2 text-xs text-green-700 bg-green-50 rounded px-2 py-1">
          Best price at <strong>{cheapestStore}</strong>
        </div>
      )}
    </div>
  );
});

// Product type group with expandable list
const ProductTypeGroup = memo(function ProductTypeGroup({
  typeName,
  products,
  onSelectProduct,
}: {
  typeName: string;
  products: BrandMatchResult[];
  onSelectProduct: (product: BrandMatchResult) => void;
}) {
  const [expanded, setExpanded] = useState(true);

  // Sort products by number of stores (more availability first)
  const sortedProducts = useMemo(
    () => [...products].sort((a, b) => b.stores.length - a.stores.length),
    [products]
  );

  return (
    <div className="bg-white rounded-xl border overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex justify-between items-center bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <h3 className="font-semibold text-gray-900">{typeName}</h3>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">
            {products.length} product{products.length > 1 ? 's' : ''}
          </span>
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {expanded && (
        <div className="p-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {sortedProducts.map((product) => (
            <ProductCompareCard
              key={`${product.brand}-${product.product_name}-${product.size}`}
              product={product}
              onClick={() => onSelectProduct(product)}
            />
          ))}
        </div>
      )}
    </div>
  );
});

// Detail modal showing full comparison
const ProductCompareDetail = memo(function ProductCompareDetail({
  product,
  onClose,
}: {
  product: BrandMatchResult;
  onClose: () => void;
}) {
  const prices = product.stores.map((s) => parseFloat(s.price.replace('$', '')));
  const cheapestPrice = Math.min(...prices);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-lg font-bold text-gray-900">{product.product_name}</h2>
              <p className="text-sm text-gray-500">
                {product.brand && `${product.brand} • `}
                {product.size}
              </p>
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
        </div>

        {/* Store prices */}
        <div className="p-4 overflow-y-auto max-h-[60vh] space-y-2">
          {product.stores
            .sort((a, b) => parseFloat(a.price.replace('$', '')) - parseFloat(b.price.replace('$', '')))
            .map((store) => {
              const price = parseFloat(store.price.replace('$', ''));
              const isCheapest = price === cheapestPrice;

              return (
                <div
                  key={store.special_id}
                  className={`flex items-center gap-3 p-3 rounded-lg ${
                    isCheapest ? 'bg-green-50 border border-green-200' : 'bg-gray-50'
                  }`}
                >
                  {/* Store badge */}
                  <span
                    className={`${STORE_COLORS[store.store_slug] || 'bg-gray-500'} text-white text-xs font-medium px-2 py-1 rounded`}
                  >
                    {store.store_name}
                  </span>

                  {/* Image */}
                  {store.image_url && (
                    <img
                      src={store.image_url}
                      alt=""
                      className="w-10 h-10 object-contain rounded"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none';
                      }}
                    />
                  )}

                  {/* Price */}
                  <div className="flex-1">
                    <div className="flex items-baseline gap-2">
                      <span className={`text-lg font-bold ${isCheapest ? 'text-green-600' : 'text-gray-900'}`}>
                        {store.price}
                      </span>
                      {store.was_price && (
                        <span className="text-sm text-gray-400 line-through">{store.was_price}</span>
                      )}
                    </div>
                    {store.unit_price && (
                      <span className="text-xs text-gray-500">{store.unit_price}</span>
                    )}
                  </div>

                  {/* Discount badge */}
                  {store.discount_percent && store.discount_percent > 0 && (
                    <span
                      className={`text-xs font-bold px-2 py-1 rounded-full ${
                        store.discount_percent >= 50 ? 'bg-red-100 text-red-600' : 'bg-orange-100 text-orange-600'
                      }`}
                    >
                      {store.discount_percent}% OFF
                    </span>
                  )}

                  {/* Cheapest badge */}
                  {isCheapest && (
                    <span className="bg-green-500 text-white text-xs font-bold px-2 py-1 rounded-full">
                      BEST
                    </span>
                  )}

                  {/* Link */}
                  {store.product_url && (
                    <a
                      href={store.product_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 text-sm"
                      onClick={(e) => e.stopPropagation()}
                    >
                      View
                    </a>
                  )}
                </div>
              );
            })}
        </div>

        {/* Footer with savings */}
        <div className="p-4 border-t bg-gray-50">
          {product.savings_potential && (
            <div className="text-center text-sm text-green-700 mb-3">
              Save up to <strong>{product.savings_potential}</strong> by shopping at{' '}
              <strong>{product.cheapest_store}</strong>
            </div>
          )}
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
});

export function ComparePage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedProduct, setSelectedProduct] = useState<BrandMatchResult | null>(null);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const { data: results, isLoading, error } = useBrandMatch(debouncedSearch);

  // Group results by product type
  const groupedResults = useMemo(() => {
    if (!results || results.length === 0) return {};
    return groupByProductType(results);
  }, [results]);

  const hasResults = Object.keys(groupedResults).length > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-indigo-700 rounded-2xl p-6 text-white">
        <h1 className="text-3xl font-bold mb-2">Compare Products</h1>
        <p className="text-purple-100">
          Find the best prices for identical products across Woolworths, Coles, ALDI & IGA
        </p>
      </div>

      {/* Fresh Foods Section */}
      <FreshFoodsSection />

      {/* Search Section */}
      <div className="bg-white rounded-xl border p-4">
        <div className="relative">
          <input
            type="text"
            placeholder="Search for a product (e.g., Cadbury Dairy Milk, Coca Cola, Milk 2L)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-3 text-lg border-2 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
          />
          <svg
            className="absolute left-3 top-3.5 h-6 w-6 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          {isLoading && (
            <div className="absolute right-3 top-3.5">
              <div className="animate-spin h-6 w-6 border-2 border-purple-600 border-t-transparent rounded-full" />
            </div>
          )}
        </div>

        {/* Popular searches */}
        <div className="mt-4 flex flex-wrap gap-2">
          <span className="text-sm text-gray-500">Popular:</span>
          {POPULAR_SEARCHES.map((term) => (
            <button
              key={term}
              onClick={() => setSearchQuery(term)}
              className={`px-3 py-1 text-sm rounded-full transition-colors ${
                searchQuery === term
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {term}
            </button>
          ))}
        </div>
      </div>

      {/* Results */}
      {debouncedSearch.length >= 2 ? (
        error ? (
          <div className="bg-white rounded-xl border p-12 text-center">
            <div className="text-5xl mb-4">❌</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Error loading results</h3>
            <p className="text-gray-500">Please try again later</p>
          </div>
        ) : isLoading ? (
          <div className="bg-white rounded-xl border p-12 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto" />
            <p className="text-gray-500 mt-4">Searching across all stores...</p>
          </div>
        ) : hasResults ? (
          <div className="space-y-4">
            <p className="text-gray-500">
              Found {results?.length} products matching "{debouncedSearch}"
            </p>

            {Object.entries(groupedResults).map(([type, products]) => (
              <ProductTypeGroup
                key={type}
                typeName={type}
                products={products}
                onSelectProduct={setSelectedProduct}
              />
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-xl border p-12 text-center">
            <div className="text-5xl mb-4">🔍</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No products found</h3>
            <p className="text-gray-500">
              No products matching "{debouncedSearch}" are currently on special at multiple stores.
            </p>
            <p className="text-sm text-gray-400 mt-2">
              Try a different search term or check back later for new specials.
            </p>
          </div>
        )
      ) : (
        <div className="bg-white rounded-xl border p-12 text-center">
          <div className="text-5xl mb-4">🛒</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">Search for products to compare</h3>
          <p className="text-gray-500 max-w-md mx-auto">
            Enter a product name above to find the best prices across Woolworths, Coles, ALDI, and IGA.
          </p>
          <p className="text-sm text-gray-400 mt-4">
            Only products currently on special at multiple stores will be shown.
          </p>
        </div>
      )}

      {/* Detail Modal */}
      {selectedProduct && (
        <ProductCompareDetail
          product={selectedProduct}
          onClose={() => setSelectedProduct(null)}
        />
      )}
    </div>
  );
}
