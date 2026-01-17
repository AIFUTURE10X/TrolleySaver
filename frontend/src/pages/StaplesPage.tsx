import { useState, useMemo } from 'react';
import { useStaplesInfinite, useStaplesCategories, type StaplesFilters } from '../api/hooks';
import { StapleCard } from '../components/StapleCard';
import { StaplesBasket, BasketButton } from '../components/StaplesBasket';
import { useStaplesBasket } from '../hooks/useStaplesBasket';
import type { StapleProduct } from '../types';

const SORT_OPTIONS = [
  { value: 'name', label: 'Name A-Z' },
  { value: 'price_low', label: 'Price: Low to High' },
  { value: 'price_high', label: 'Price: High to Low' },
  { value: 'savings', label: 'Biggest Savings' },
] as const;

const STORES = [
  {
    slug: 'woolworths',
    name: 'Woolworths',
    color: 'bg-green-600 hover:bg-green-700',
    textColor: 'text-white',
    borderColor: 'border-green-600',
    inactiveColor: 'bg-green-50 text-green-700 hover:bg-green-100 border-green-200',
  },
  {
    slug: 'coles',
    name: 'Coles',
    color: 'bg-red-600 hover:bg-red-700',
    textColor: 'text-white',
    borderColor: 'border-red-600',
    inactiveColor: 'bg-red-50 text-red-700 hover:bg-red-100 border-red-200',
  },
  {
    slug: 'aldi',
    name: 'ALDI',
    color: 'bg-blue-600 hover:bg-blue-700',
    textColor: 'text-white',
    borderColor: 'border-blue-600',
    inactiveColor: 'bg-blue-50 text-blue-700 hover:bg-blue-100 border-blue-200',
  },
  {
    slug: 'iga',
    name: 'IGA',
    color: 'bg-orange-500 hover:bg-orange-600',
    textColor: 'text-white',
    borderColor: 'border-orange-500',
    inactiveColor: 'bg-orange-50 text-orange-700 hover:bg-orange-100 border-orange-200',
  },
] as const;

// Store icon component with brand colors
function StoreIcon({ store }: { store: string }) {
  switch (store) {
    case 'woolworths':
      return (
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
          <circle cx="12" cy="12" r="10" fill="#1e8e3e" />
          <text x="12" y="16" textAnchor="middle" fontSize="12" fill="white" fontWeight="bold">W</text>
        </svg>
      );
    case 'coles':
      return (
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
          <circle cx="12" cy="12" r="10" fill="#e01a22" />
          <text x="12" y="16" textAnchor="middle" fontSize="12" fill="white" fontWeight="bold">C</text>
        </svg>
      );
    case 'aldi':
      return (
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
          <circle cx="12" cy="12" r="10" fill="#00457c" />
          <text x="12" y="16" textAnchor="middle" fontSize="12" fill="white" fontWeight="bold">A</text>
        </svg>
      );
    case 'iga':
      return (
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
          <circle cx="12" cy="12" r="10" fill="#f7941d" />
          <text x="12" y="16" textAnchor="middle" fontSize="11" fill="white" fontWeight="bold">I</text>
        </svg>
      );
    default:
      return null;
  }
}

export function StaplesPage() {
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>(undefined);
  const [selectedStore, setSelectedStore] = useState<string | undefined>(undefined);
  const [sortBy, setSortBy] = useState<StaplesFilters['sort']>('name');
  const [searchQuery, setSearchQuery] = useState('');
  const [isBasketOpen, setIsBasketOpen] = useState(false);

  const basket = useStaplesBasket();

  // Build filters
  const filters: Omit<StaplesFilters, 'offset'> = useMemo(
    () => ({
      category: selectedCategory,
      store: selectedStore,
      sort: sortBy,
      search: searchQuery.length >= 2 ? searchQuery : undefined,
      limit: 100,
    }),
    [selectedCategory, selectedStore, sortBy, searchQuery]
  );

  const {
    data: staplesData,
    isLoading: isLoadingStaples,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useStaplesInfinite(filters);
  const { data: categoriesData, isLoading: isLoadingCategories } = useStaplesCategories();

  // Flatten paginated data into a single products array
  const allProducts = useMemo(() => {
    if (!staplesData?.pages) return [];
    return staplesData.pages.flatMap(page => page.products);
  }, [staplesData]);

  const totalProducts = staplesData?.pages[0]?.total ?? 0;

  const handleAddToBasket = (product: StapleProduct) => {
    if (basket.isInBasket(product.id)) {
      basket.removeItem(product.id);
    } else {
      basket.addItem(product.id, product.name);
    }
  };

  return (
    <div className="min-h-screen">
      {/* Header with Stats */}
      <div className="bg-gradient-to-r from-teal-600 to-cyan-700 rounded-2xl p-6 text-white mb-6">
        <h1 className="text-3xl font-bold mb-2">Everyday Essentials</h1>
        <p className="text-teal-100 mb-4">
          Compare prices on fresh produce & meat across all stores
        </p>

        <div className="flex flex-wrap gap-4 text-sm items-center">
          {/* Page Navigation Buttons */}
          <a
            href="/"
            className="px-5 py-2 rounded-full font-semibold text-sm transition-all bg-orange-500 hover:bg-orange-400 text-white shadow-lg"
          >
            Specials
          </a>
          <a
            href="/staples"
            className="px-5 py-2 rounded-full font-semibold text-sm transition-all bg-emerald-500 hover:bg-emerald-400 text-white shadow-lg ring-2 ring-white"
          >
            Staples
          </a>
          <a
            href="/compare"
            className="px-5 py-2 rounded-full font-semibold text-sm transition-all bg-pink-500 hover:bg-pink-400 text-white shadow-lg"
          >
            Compare
          </a>

          <div className="bg-white/20 rounded-lg px-4 py-2">
            <span className="font-bold text-xl">{totalProducts}</span>
            <span className="ml-2">Products</span>
          </div>
          <div className="bg-white/20 rounded-lg px-4 py-2">
            <span className="font-bold text-xl">4</span>
            <span className="ml-2">Stores</span>
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="mb-6">
        <input
          type="text"
          placeholder="Search for products..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {/* Category & Store Tabs */}
      <div className="mb-6 overflow-x-auto">
        <div className="flex flex-wrap gap-2 pb-2 items-center">
          {/* Category Buttons */}
          <button
            onClick={() => setSelectedCategory(undefined)}
            className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
              !selectedCategory
                ? 'bg-gray-900 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            All Products
          </button>
          {isLoadingCategories ? (
            <span className="px-4 py-2 text-gray-400">Loading categories...</span>
          ) : (
            categoriesData?.categories.map((category) => (
              <button
                key={category.slug}
                onClick={() => setSelectedCategory(category.slug)}
                className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                  selectedCategory === category.slug
                    ? 'bg-gray-900 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {category.icon && <span className="mr-1">{category.icon}</span>}
                {category.name}
                <span className="ml-1 text-xs opacity-70">({category.count})</span>
              </button>
            ))
          )}

          {/* Separator */}
          <div className="h-6 w-px bg-gray-300 mx-2" />

          {/* Store Filter Buttons */}
          <button
            onClick={() => setSelectedStore(undefined)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors border ${
              !selectedStore
                ? 'bg-gray-800 text-white border-gray-800'
                : 'bg-gray-50 text-gray-600 hover:bg-gray-100 border-gray-200'
            }`}
          >
            All Stores
          </button>
          {STORES.map((store) => (
            <button
              key={store.slug}
              onClick={() => setSelectedStore(selectedStore === store.slug ? undefined : store.slug)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors border flex items-center gap-1.5 ${
                selectedStore === store.slug
                  ? `${store.color} ${store.textColor} ${store.borderColor}`
                  : store.inactiveColor
              }`}
            >
              <StoreIcon store={store.slug} />
              {store.name}
            </button>
          ))}
        </div>
      </div>

      {/* Filters Row */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div className="text-sm text-gray-500">
          {totalProducts} products
          {selectedCategory && ` in ${categoriesData?.categories.find(c => c.slug === selectedCategory)?.name || selectedCategory}`}
          {selectedStore && ` from ${STORES.find(s => s.slug === selectedStore)?.name || selectedStore}`}
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="sort" className="text-sm text-gray-600">
            Sort by:
          </label>
          <select
            id="sort"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as StaplesFilters['sort'])}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Product Grid */}
      {isLoadingStaples ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="bg-white rounded-xl shadow-sm border animate-pulse">
              <div className="aspect-square bg-gray-200" />
              <div className="p-4 space-y-3">
                <div className="h-4 bg-gray-200 rounded w-3/4" />
                <div className="h-4 bg-gray-200 rounded w-1/2" />
                <div className="space-y-2">
                  <div className="h-3 bg-gray-200 rounded" />
                  <div className="h-3 bg-gray-200 rounded" />
                  <div className="h-3 bg-gray-200 rounded" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="text-center py-12">
          <p className="text-red-500">Error loading products. Please try again.</p>
        </div>
      ) : allProducts.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500 text-lg">No products found</p>
          <p className="text-gray-400 mt-2">
            Try adjusting your search or filters
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-4">
          {allProducts.map((product, index) => (
            <StapleCard
              key={`${product.id}-${index}`}
              product={product}
              onAddToBasket={handleAddToBasket}
              isInBasket={basket.isInBasket(product.id)}
            />
          ))}
        </div>
      )}

      {/* Load More */}
      {hasNextPage && (
        <div className="mt-8 text-center">
          <button
            className="px-6 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
            onClick={() => fetchNextPage()}
            disabled={isFetchingNextPage}
          >
            {isFetchingNextPage ? 'Loading...' : `Load More Products (${allProducts.length} of ${totalProducts})`}
          </button>
        </div>
      )}

      {/* Basket Button */}
      <BasketButton
        itemCount={basket.totalItems}
        onClick={() => setIsBasketOpen(true)}
      />

      {/* Basket Panel */}
      <StaplesBasket
        items={basket.items}
        onRemoveItem={basket.removeItem}
        onUpdateQuantity={basket.updateQuantity}
        onIncrementQuantity={basket.incrementQuantity}
        onDecrementQuantity={basket.decrementQuantity}
        onClearBasket={basket.clearBasket}
        isOpen={isBasketOpen}
        onClose={() => setIsBasketOpen(false)}
      />
    </div>
  );
}
