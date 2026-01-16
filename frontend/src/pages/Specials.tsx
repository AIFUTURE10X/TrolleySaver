import { useEffect, useState, useCallback } from 'react';
import { getSpecials, getSpecialsStats, getSpecialsCategories, getStores } from '../api/client';
import { SpecialCard } from '../components/SpecialCard';
import type { Special, SpecialsStats, CategoryCount, Store } from '../types';

const STORE_COLORS: Record<string, string> = {
  woolworths: 'bg-[#00A651]',
  coles: 'bg-[#E01A22]',
  aldi: 'bg-[#00448C]',
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

export function Specials() {
  const [specials, setSpecials] = useState<Special[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [stats, setStats] = useState<SpecialsStats | null>(null);
  const [categories, setCategories] = useState<CategoryCount[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  // Filters
  const [selectedStore, setSelectedStore] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [minDiscount, setMinDiscount] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sort, setSort] = useState<'discount' | 'price' | 'name'>('discount');

  // Pagination
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [total, setTotal] = useState(0);

  const LIMIT = 24;

  // Load initial data
  useEffect(() => {
    async function loadInitialData() {
      try {
        const [storesData, statsData, categoriesData] = await Promise.all([
          getStores(),
          getSpecialsStats(),
          getSpecialsCategories(),
        ]);
        setStores(storesData);
        setStats(statsData);
        setCategories(categoriesData);
      } catch (error) {
        console.error('Failed to load initial data:', error);
      }
    }
    loadInitialData();
  }, []);

  // Load specials when filters change
  const loadSpecials = useCallback(async (resetPage = true) => {
    try {
      if (resetPage) {
        setLoading(true);
        setPage(1);
      } else {
        setLoadingMore(true);
      }

      const currentPage = resetPage ? 1 : page;
      const result = await getSpecials({
        store: selectedStore || undefined,
        category: selectedCategory || undefined,
        min_discount: minDiscount || undefined,
        search: searchQuery || undefined,
        sort,
        page: currentPage,
        limit: LIMIT,
      });

      if (resetPage) {
        setSpecials(result.items);
      } else {
        setSpecials((prev) => [...prev, ...result.items]);
      }
      setTotal(result.total);
      setHasMore(result.has_more);
    } catch (error) {
      console.error('Failed to load specials:', error);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [selectedStore, selectedCategory, minDiscount, searchQuery, sort, page]);

  // Reload when filters change
  useEffect(() => {
    loadSpecials(true);
  }, [selectedStore, selectedCategory, minDiscount, sort]);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchQuery.length === 0 || searchQuery.length >= 2) {
        loadSpecials(true);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Load more
  const handleLoadMore = () => {
    setPage((p) => p + 1);
  };

  useEffect(() => {
    if (page > 1) {
      loadSpecials(false);
    }
  }, [page]);

  const clearFilters = () => {
    setSelectedStore('');
    setSelectedCategory('');
    setMinDiscount(0);
    setSearchQuery('');
    setSort('discount');
  };

  const hasActiveFilters = selectedStore || selectedCategory || minDiscount > 0 || searchQuery;

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
                <span>Updated: {new Date(stats.last_updated).toLocaleDateString()}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Store Tabs */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setSelectedStore('')}
          className={`px-5 py-2.5 rounded-full font-medium text-sm transition-all ${
            !selectedStore
              ? 'bg-gray-900 text-white shadow-lg'
              : 'bg-white text-gray-600 hover:bg-gray-100 border'
          }`}
        >
          All Stores
          {stats && (
            <span className="ml-2 text-xs opacity-75">({stats.total_specials})</span>
          )}
        </button>
        {stores.map((store) => (
          <button
            key={store.id}
            onClick={() => setSelectedStore(store.slug)}
            className={`px-5 py-2.5 rounded-full font-medium text-sm transition-all ${
              selectedStore === store.slug
                ? `${STORE_COLORS[store.slug]} text-white shadow-lg`
                : 'bg-white text-gray-600 hover:bg-gray-100 border'
            }`}
          >
            {store.name}
            {stats?.by_store[store.slug] !== undefined && (
              <span className="ml-2 text-xs opacity-75">({stats.by_store[store.slug]})</span>
            )}
          </button>
        ))}
      </div>

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
            className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
          >
            {DISCOUNT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          {/* Category Filter */}
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat.name} value={cat.name}>
                {cat.name} ({cat.count})
              </option>
            ))}
          </select>

          {/* Sort */}
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as 'discount' | 'price' | 'name')}
            className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
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
          {loading ? 'Loading...' : `Showing ${specials.length} of ${total} specials`}
        </p>
      </div>

      {/* Loading State */}
      {loading ? (
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
        </div>
      ) : specials.length > 0 ? (
        <>
          {/* Specials Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-4">
            {specials.map((special) => (
              <SpecialCard key={special.id} special={special} />
            ))}
          </div>

          {/* Load More */}
          {hasMore && (
            <div className="flex justify-center pt-4">
              <button
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="px-8 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loadingMore ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Loading...
                  </span>
                ) : (
                  `Load More (${total - specials.length} remaining)`
                )}
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="bg-white rounded-xl border p-12 text-center">
          <div className="text-5xl mb-4">🏷️</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No specials found</h3>
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
  );
}
