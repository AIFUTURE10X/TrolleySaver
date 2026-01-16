/**
 * Optimized Specials Page V2
 *
 * Performance improvements:
 * - React Query for caching (no refetch on filter toggle back)
 * - Intersection Observer for infinite scroll (no manual "Load More")
 * - Image lazy loading (native browser support)
 * - Memoized components (prevent unnecessary re-renders)
 * - Debounced search
 */
import { useState, useCallback, useRef, useEffect, memo, useMemo } from 'react';
import {
  useStores,
  useStats,
  useCategoryTree,
  useSpecialsInfinite,
  usePrefetchSpecials,
  type SpecialsFilters,
} from '../api/hooks';
import type { Special, Store } from '../types';
import { CategoryTabs } from '../components/CategoryNav/CategoryTabs';
import { CategorySidebar } from '../components/CategoryNav/CategorySidebar';
import { FilterChips } from '../components/FilterChips';
import { CompareView } from '../components/Compare/CompareView';

const STORE_COLORS: Record<string, string> = {
  woolworths: 'bg-[#00A651]',
  coles: 'bg-[#E01A22]',
  aldi: 'bg-[#00448C]',
  iga: 'bg-[#FF6B00]',
};

const DISCOUNT_OPTIONS = [
  { value: 0, label: 'All Discounts' },
  { value: 25, label: '25%+ Off' },
  { value: 50, label: '50%+ Off (Half Price)' },
  { value: 75, label: '75%+ Off' },
];

const SORT_OPTIONS = [
  { value: 'discount', label: 'Biggest Discount' },
  { value: 'price', label: 'Lowest Price' },
  { value: 'name', label: 'Name A-Z' },
];

// Memoized Product Card for performance
const ProductCard = memo(function ProductCard({
  product,
  onCompare,
}: {
  product: Special;
  onCompare?: (product: Special) => void;
}) {
  const discountBadgeColor =
    (product.discount_percent || 0) >= 50 ? 'bg-red-500' : 'bg-orange-500';

  return (
    <div className="bg-white rounded-xl border hover:shadow-lg transition-shadow overflow-hidden group">
      {/* Discount Badge */}
      <div className="relative">
        <span
          className={`absolute top-2 left-2 ${discountBadgeColor} text-white text-xs font-bold px-2 py-1 rounded-full z-10`}
        >
          {product.discount_percent}% OFF
        </span>

        {/* Compare button (appears on hover) */}
        {onCompare && (
          <button
            onClick={() => onCompare(product)}
            className="absolute top-2 right-2 bg-white/90 hover:bg-white text-blue-600 text-xs font-medium px-2 py-1 rounded-full z-10 opacity-0 group-hover:opacity-100 transition-opacity shadow"
          >
            Compare
          </button>
        )}

        {/* Image with lazy loading */}
        <div className="aspect-square bg-gray-50 flex items-center justify-center p-4">
          <img
            src={product.image_url || '/placeholder-product.svg'}
            alt={product.name}
            loading="lazy"
            decoding="async"
            className="max-h-full max-w-full object-contain group-hover:scale-105 transition-transform"
            onError={(e) => {
              (e.target as HTMLImageElement).src = '/placeholder-product.svg';
            }}
          />
        </div>

        {/* Store badge */}
        <span
          className={`absolute bottom-2 right-2 ${
            STORE_COLORS[product.store_slug || ''] || 'bg-gray-500'
          } text-white text-xs px-2 py-0.5 rounded`}
        >
          {product.store_name}
        </span>
      </div>

      {/* Product Info */}
      <div className="p-3">
        <h3 className="font-medium text-sm text-gray-900 line-clamp-2 min-h-[2.5rem]">
          {product.name}
        </h3>

        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-lg font-bold text-green-600">
            ${product.price}
          </span>
          {product.was_price && (
            <span className="text-sm text-gray-400 line-through">
              ${product.was_price}
            </span>
          )}
        </div>
      </div>

      {/* View Link */}
      {product.product_url && (
        <a
          href={product.product_url}
          target="_blank"
          rel="noopener noreferrer"
          className="block text-center py-2 text-sm text-blue-600 hover:bg-blue-50 border-t transition-colors"
        >
          View at {product.store_name}
        </a>
      )}
    </div>
  );
});

// Store Tab Button with prefetch on hover
const StoreTab = memo(function StoreTab({
  store,
  isSelected,
  count,
  onClick,
  onHover,
}: {
  store?: Store;
  isSelected: boolean;
  count?: number;
  onClick: () => void;
  onHover: () => void;
}) {
  const slug = store?.slug || '';
  const name = store?.name || 'All Stores';

  return (
    <button
      onClick={onClick}
      onMouseEnter={onHover}
      className={`px-5 py-2.5 rounded-full font-medium text-sm transition-all ${
        isSelected
          ? slug
            ? `${STORE_COLORS[slug]} text-white shadow-lg`
            : 'bg-gray-900 text-white shadow-lg'
          : 'bg-white text-gray-600 hover:bg-gray-100 border'
      }`}
    >
      {name}
      {count !== undefined && (
        <span className="ml-2 text-xs opacity-75">({count})</span>
      )}
    </button>
  );
});

// Infinite scroll trigger
function LoadMoreTrigger({
  onLoadMore,
  hasMore,
  isLoading,
}: {
  onLoadMore: () => void;
  hasMore: boolean;
  isLoading: boolean;
}) {
  const triggerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!hasMore || isLoading) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          onLoadMore();
        }
      },
      { rootMargin: '200px' }
    );

    if (triggerRef.current) {
      observer.observe(triggerRef.current);
    }

    return () => observer.disconnect();
  }, [hasMore, isLoading, onLoadMore]);

  if (!hasMore) return null;

  return (
    <div ref={triggerRef} className="flex justify-center py-8">
      {isLoading && (
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      )}
    </div>
  );
}

export function SpecialsV2() {
  // Filters state
  const [selectedStore, setSelectedStore] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(null);
  const [minDiscount, setMinDiscount] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [debouncedSearch, setDebouncedSearch] = useState<string>('');
  const [sort, setSort] = useState<'discount' | 'price' | 'name'>('discount');

  // Compare modal state
  const [compareProduct, setCompareProduct] = useState<Special | null>(null);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Build filters object
  const filters: SpecialsFilters = useMemo(
    () => ({
      store: selectedStore || undefined,
      category: selectedCategory || undefined,
      category_id: selectedCategoryId || undefined,
      min_discount: minDiscount || undefined,
      search: debouncedSearch || undefined,
      sort,
    }),
    [selectedStore, selectedCategory, selectedCategoryId, minDiscount, debouncedSearch, sort]
  );

  // React Query hooks
  const { data: stores = [] } = useStores();
  const { data: stats } = useStats();
  const { data: categoryTree } = useCategoryTree();
  const {
    data: specialsData,
    fetchNextPage,
    hasNextPage,
    isFetching,
    isFetchingNextPage,
    isLoading,
  } = useSpecialsInfinite(filters);

  // Prefetch for store tabs
  const prefetch = usePrefetchSpecials();

  // Flatten pages into single array
  const specials = useMemo(
    () => specialsData?.pages.flatMap((page) => page.items) ?? [],
    [specialsData]
  );

  const total = specialsData?.pages[0]?.total ?? 0;

  // Handlers
  const handleStoreClick = useCallback((slug: string) => {
    setSelectedStore(slug);
  }, []);

  const handleStorePrefetch = useCallback(
    (slug: string) => {
      prefetch({ ...filters, store: slug || undefined });
    },
    [prefetch, filters]
  );

  const handleLoadMore = useCallback(() => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const clearFilters = useCallback(() => {
    setSelectedStore('');
    setSelectedCategory('');
    setSelectedCategoryId(null);
    setMinDiscount(0);
    setSearchQuery('');
    setSort('discount');
  }, []);

  // Handle category selection from CategoryTabs
  const handleCategorySelect = useCallback((categoryId: number | null) => {
    setSelectedCategoryId(categoryId);
    // Clear the old string-based category when using unified categories
    setSelectedCategory('');
  }, []);

  // Handle compare modal
  const handleCompare = useCallback((product: Special) => {
    setCompareProduct(product);
  }, []);

  const handleCloseCompare = useCallback(() => {
    setCompareProduct(null);
  }, []);

  const hasActiveFilters =
    selectedStore || selectedCategory || selectedCategoryId || minDiscount > 0 || searchQuery;

  return (
    <div className="space-y-6">
      {/* Header with Stats */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-2xl p-6 text-white">
        <h1 className="text-3xl font-bold mb-2">Weekly Specials</h1>
        <p className="text-blue-100 mb-4">
          Find the best deals from Woolworths, Coles & ALDI
        </p>

        {stats && (
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="bg-white/20 rounded-lg px-4 py-2">
              <span className="font-bold text-xl">{stats.total_specials}</span>
              <span className="ml-2">Total Specials</span>
            </div>
            <div className="bg-white/20 rounded-lg px-4 py-2">
              <span className="font-bold text-xl">{stats.half_price_count}</span>
              <span className="ml-2">Half Price or Better</span>
            </div>
            {stats.last_updated && (
              <div className="bg-white/20 rounded-lg px-4 py-2">
                Updated: {new Date(stats.last_updated).toLocaleDateString()}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Store Tabs with Prefetch */}
      <div className="flex flex-wrap gap-2">
        <StoreTab
          isSelected={!selectedStore}
          count={stats?.total_specials}
          onClick={() => handleStoreClick('')}
          onHover={() => handleStorePrefetch('')}
        />
        {stores.map((store) => (
          <StoreTab
            key={store.id}
            store={store}
            isSelected={selectedStore === store.slug}
            count={stats?.by_store[store.slug]}
            onClick={() => handleStoreClick(store.slug)}
            onHover={() => handleStorePrefetch(store.slug)}
          />
        ))}
      </div>

      {/* Mobile Category Tabs - hidden on desktop */}
      {categoryTree && (
        <div className="lg:hidden bg-white rounded-xl border p-2">
          <CategoryTabs
            categories={categoryTree.categories}
            selectedCategoryId={selectedCategoryId}
            onSelectCategory={handleCategorySelect}
            totalCount={categoryTree.total_categorized}
          />
        </div>
      )}

      {/* Main Content with Sidebar Layout */}
      <div className="flex gap-6">
        {/* Category Sidebar - hidden on mobile, visible on desktop */}
        {categoryTree && (
          <div className="hidden lg:block w-72 flex-shrink-0">
            <div className="sticky top-4">
              <CategorySidebar
                categories={categoryTree.categories}
                selectedCategoryId={selectedCategoryId}
                onSelectCategory={handleCategorySelect}
              />
            </div>
          </div>
        )}

        {/* Main Content Area */}
        <div className="flex-1 min-w-0 space-y-4">
          {/* Quick Discount Filter Chips */}
          <FilterChips
            minDiscount={minDiscount}
            onDiscountSelect={setMinDiscount}
          />

          {/* Filters Row */}
          <div className="bg-white rounded-xl border p-4">
            <div className="flex flex-wrap gap-4">
              {/* Search */}
              <div className="flex-1 min-w-[200px]">
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search specials..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <svg
                    className="absolute left-3 top-2.5 h-5 w-5 text-gray-400"
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
                </div>
              </div>

              {/* Discount Filter */}
              <select
                value={minDiscount}
                onChange={(e) => setMinDiscount(Number(e.target.value))}
                className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
              >
                {DISCOUNT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>

              {/* Sort */}
              <select
                value={sort}
                onChange={(e) =>
                  setSort(e.target.value as 'discount' | 'price' | 'name')
                }
                className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
              >
                {SORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>

              {/* Clear Filters */}
              {hasActiveFilters && (
                <button
                  onClick={clearFilters}
                  className="px-4 py-2 text-sm text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors"
                >
                  Clear Filters
                </button>
              )}
            </div>
          </div>

          {/* Results Count */}
          <div className="flex justify-between items-center">
            <p className="text-gray-500">
              {isLoading
                ? 'Loading...'
                : `Showing ${specials.length} of ${total} specials`}
            </p>
            {isFetching && !isLoading && (
              <span className="text-sm text-blue-600">Updating...</span>
            )}
          </div>

          {/* Loading State */}
          {isLoading ? (
            <div className="flex items-center justify-center min-h-[400px]">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
            </div>
          ) : specials.length > 0 ? (
            <>
              {/* Products Grid - adjusted columns for sidebar layout */}
              <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4">
                {specials.map((special) => (
                  <ProductCard
                    key={special.id}
                    product={special}
                    onCompare={handleCompare}
                  />
                ))}
              </div>

              {/* Infinite Scroll Trigger */}
              <LoadMoreTrigger
                onLoadMore={handleLoadMore}
                hasMore={!!hasNextPage}
                isLoading={isFetchingNextPage}
              />
            </>
          ) : (
            <div className="bg-white rounded-xl border p-12 text-center">
              <div className="text-5xl mb-4">🔍</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No specials found
              </h3>
              <p className="text-gray-500 max-w-md mx-auto">
                {hasActiveFilters
                  ? 'No specials match your filters. Try adjusting your search or clearing filters.'
                  : 'There are no specials available at the moment. Check back on Wednesday for new deals!'}
              </p>
              {hasActiveFilters && (
                <button
                  onClick={clearFilters}
                  className="mt-4 px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Clear Filters
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Compare Modal */}
      {compareProduct && (
        <CompareView special={compareProduct} onClose={handleCloseCompare} />
      )}
    </div>
  );
}
