/**
 * React Query hooks for data fetching with caching.
 *
 * Benefits:
 * - Automatic caching (no refetch on filter toggle back)
 * - Background refetching (stale-while-revalidate)
 * - Deduplication of concurrent requests
 * - Optimistic updates
 * - Prefetching on hover
 */
import {
  useQuery,
  useInfiniteQuery,
  useQueryClient,
  QueryClient,
} from '@tanstack/react-query';
import type {
  Store,
  Special,
  SpecialsStats,
  CategoryCount,
  CategoryTreeResponse,
  BrandMatchResult,
  TypeMatchResult,
  BrandProductsResult,
  FreshFoodsResponse,
  StaplesListResponse,
  StaplesCategoriesResponse,
  StapleProduct,
  BasketItem,
  BasketCompareResponse,
} from '../types';

// Use Railway backend URL in production, relative path in development
const API_BASE = import.meta.env.VITE_API_URL || '/api';

// Use v1 API for now (v2 has routing issues)
const USE_V2_API = false;
const SPECIALS_BASE = USE_V2_API ? '/v2/specials' : '/specials';

// Query keys for cache management
export const queryKeys = {
  stores: ['stores'] as const,
  stats: ['stats'] as const,
  categories: ['categories'] as const,
  categoryTree: ['categoryTree'] as const,
  specials: (filters: SpecialsFilters) => ['specials', filters] as const,
  product: (id: number) => ['product', id] as const,
  brandMatch: (search: string) => ['brandMatch', search] as const,
  typeMatch: (id: number) => ['typeMatch', id] as const,
  brandProducts: (id: number) => ['brandProducts', id] as const,
  freshFoods: ['freshFoods'] as const,
  // Staples keys
  staples: (filters: StaplesFilters) => ['staples', filters] as const,
  staplesCategories: ['staplesCategories'] as const,
  staple: (id: number) => ['staple', id] as const,
  basketCompare: (items: BasketItem[]) => ['basketCompare', items] as const,
};

// Types
export interface SpecialsFilters {
  store?: string;
  category?: string;
  category_id?: number;  // Unified category filter
  min_discount?: number;
  search?: string;
  sort?: 'discount' | 'price' | 'name';
}

export interface StaplesFilters {
  category?: string;
  store?: string;
  sort?: 'name' | 'price_low' | 'price_high' | 'savings';
  search?: string;
  limit?: number;
  offset?: number;
}

// Fetch helper
async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`);
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }
  return response.json();
}

// Configure query client with optimal settings
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Keep data fresh for 5 minutes
        staleTime: 5 * 60 * 1000,
        // Cache data for 30 minutes
        gcTime: 30 * 60 * 1000,
        // Retry failed requests twice
        retry: 2,
        // Don't refetch on window focus (data changes weekly)
        refetchOnWindowFocus: false,
        // Don't refetch on reconnect
        refetchOnReconnect: false,
      },
    },
  });
}

/**
 * Hook for fetching stores (rarely changes)
 */
export function useStores() {
  return useQuery({
    queryKey: queryKeys.stores,
    queryFn: () => fetchJson<Store[]>(`${SPECIALS_BASE}/stores`),
    staleTime: 60 * 60 * 1000, // 1 hour - stores never change
  });
}

/**
 * Hook for fetching stats (changes on scrape)
 */
export function useStats() {
  return useQuery({
    queryKey: queryKeys.stats,
    queryFn: () => fetchJson<SpecialsStats>(`${SPECIALS_BASE}/stats`),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook for fetching categories (changes weekly)
 */
export function useCategories() {
  return useQuery({
    queryKey: queryKeys.categories,
    queryFn: () => fetchJson<CategoryCount[]>(`${SPECIALS_BASE}/categories`),
    staleTime: 30 * 60 * 1000, // 30 minutes
  });
}

// V1 API response type (page-based pagination)
interface SpecialsPageV1 {
  items: Special[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

/**
 * Hook for infinite scrolling specials list
 * Uses page-based pagination with v1 API
 */
export function useSpecialsInfinite(filters: SpecialsFilters) {
  return useInfiniteQuery({
    queryKey: queryKeys.specials(filters),
    queryFn: async ({ pageParam = 1 }) => {
      const params = new URLSearchParams();
      if (filters.store) params.set('store', filters.store);
      if (filters.category) params.set('category', filters.category);
      if (filters.category_id) params.set('category_id', String(filters.category_id));
      if (filters.min_discount) params.set('min_discount', String(filters.min_discount));
      if (filters.search) params.set('search', filters.search);
      if (filters.sort) params.set('sort', filters.sort);
      params.set('page', String(pageParam));
      params.set('limit', '50');

      const query = params.toString();
      // Note: API expects trailing slash before query params
      const data = await fetchJson<SpecialsPageV1>(`${SPECIALS_BASE}/${query ? `?${query}` : ''}`);

      // Normalize response to match v2 format for frontend consistency
      return {
        items: data.items,
        total: data.total,
        cursor: data.has_more ? String(pageParam + 1) : null,
        has_more: data.has_more,
        page: data.page,
      };
    },
    initialPageParam: 1,
    getNextPageParam: (lastPage) => lastPage.has_more ? lastPage.page + 1 : undefined,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Hook for fetching single product details
 */
export function useProduct(id: number) {
  return useQuery({
    queryKey: queryKeys.product(id),
    queryFn: () => fetchJson<Special>(`${SPECIALS_BASE}/${id}`),
    enabled: id > 0,
    staleTime: 60 * 60 * 1000, // 1 hour - product data rarely changes
  });
}

/**
 * Prefetch specials for a filter combination (call on hover)
 */
export function usePrefetchSpecials() {
  const queryClient = useQueryClient();

  return (filters: SpecialsFilters) => {
    queryClient.prefetchInfiniteQuery({
      queryKey: queryKeys.specials(filters),
      queryFn: async () => {
        const params = new URLSearchParams();
        if (filters.store) params.set('store', filters.store);
        if (filters.category) params.set('category', filters.category);
        if (filters.category_id) params.set('category_id', String(filters.category_id));
        if (filters.min_discount) params.set('min_discount', String(filters.min_discount));
        if (filters.search) params.set('search', filters.search);
        if (filters.sort) params.set('sort', filters.sort);
        params.set('page', '1');
        params.set('limit', '50');

        const query = params.toString();
        // Note: API expects trailing slash before query params
        const data = await fetchJson<SpecialsPageV1>(`${SPECIALS_BASE}/${query ? `?${query}` : ''}`);

        return {
          items: data.items,
          total: data.total,
          cursor: data.has_more ? '2' : null,
          has_more: data.has_more,
          page: data.page,
        };
      },
      initialPageParam: 1,
      staleTime: 5 * 60 * 1000,
    });
  };
}

/**
 * Invalidate specials cache (call after admin actions)
 */
export function useInvalidateSpecials() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: ['specials'] });
    queryClient.invalidateQueries({ queryKey: ['stats'] });
    queryClient.invalidateQueries({ queryKey: ['categories'] });
  };
}

/**
 * Hook for fetching hierarchical category tree
 */
export function useCategoryTree() {
  return useQuery({
    queryKey: queryKeys.categoryTree,
    queryFn: () => fetchJson<CategoryTreeResponse>(`${SPECIALS_BASE}/categories/tree`),
    staleTime: 60 * 60 * 1000, // 1 hour - categories rarely change
  });
}

/**
 * Hook for searching brand matches across stores
 */
export function useBrandMatch(search: string) {
  return useQuery({
    queryKey: queryKeys.brandMatch(search),
    queryFn: () => fetchJson<BrandMatchResult[]>(`/compare/specials/brand-match?search=${encodeURIComponent(search)}`),
    enabled: search.length >= 2,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Hook for comparing similar product types
 */
export function useTypeMatch(specialId: number) {
  return useQuery({
    queryKey: queryKeys.typeMatch(specialId),
    queryFn: () => fetchJson<TypeMatchResult>(`/compare/specials/type-match/${specialId}`),
    enabled: specialId > 0,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Hook for finding all products from the same brand across stores
 */
export function useBrandProducts(specialId: number) {
  return useQuery({
    queryKey: queryKeys.brandProducts(specialId),
    queryFn: () => fetchJson<BrandProductsResult>(`/compare/specials/brand-products/${specialId}`),
    enabled: specialId > 0,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Hook for fetching fresh foods (produce and meat) prices
 * These are regular prices, not just specials
 */
export function useFreshFoods(limit: number = 50) {
  return useQuery({
    queryKey: queryKeys.freshFoods,
    queryFn: () => fetchJson<FreshFoodsResponse>(`/compare/fresh-foods?limit=${limit}`),
    staleTime: 30 * 60 * 1000, // 30 minutes - produce prices stable within day
  });
}

// ============== Staples Hooks ==============

/**
 * Hook for fetching staple products with prices from all stores
 */
export function useStaples(filters: StaplesFilters) {
  return useQuery({
    queryKey: queryKeys.staples(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.category) params.set('category', filters.category);
      if (filters.store) params.set('store', filters.store);
      if (filters.sort) params.set('sort', filters.sort);
      if (filters.search) params.set('search', filters.search);
      if (filters.limit) params.set('limit', String(filters.limit));
      if (filters.offset) params.set('offset', String(filters.offset));

      const query = params.toString();
      return fetchJson<StaplesListResponse>(`/staples/${query ? `?${query}` : ''}`);
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook for infinite scrolling staples list (Load More)
 */
export function useStaplesInfinite(filters: Omit<StaplesFilters, 'offset'>) {
  const limit = filters.limit || 100;

  return useInfiniteQuery({
    queryKey: ['staplesInfinite', filters] as const,
    queryFn: async ({ pageParam = 0 }) => {
      const params = new URLSearchParams();
      if (filters.category) params.set('category', filters.category);
      if (filters.store) params.set('store', filters.store);
      if (filters.sort) params.set('sort', filters.sort);
      if (filters.search) params.set('search', filters.search);
      params.set('limit', String(limit));
      params.set('offset', String(pageParam));

      const query = params.toString();
      const data = await fetchJson<StaplesListResponse>(`/staples/${query ? `?${query}` : ''}`);

      return {
        ...data,
        offset: pageParam,
        limit,
      };
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      if (!lastPage.has_more) return undefined;
      return lastPage.offset + lastPage.limit;
    },
    staleTime: 10 * 60 * 1000,
  });
}

/**
 * Hook for fetching staple categories with counts
 */
export function useStaplesCategories() {
  return useQuery({
    queryKey: queryKeys.staplesCategories,
    queryFn: () => fetchJson<StaplesCategoriesResponse>('/staples/categories'),
    staleTime: 30 * 60 * 1000, // 30 minutes
  });
}

/**
 * Hook for fetching a single staple product
 */
export function useStaple(productId: number) {
  return useQuery({
    queryKey: queryKeys.staple(productId),
    queryFn: () => fetchJson<StapleProduct>(`/staples/${productId}`),
    enabled: productId > 0,
    staleTime: 10 * 60 * 1000,
  });
}

/**
 * Hook for comparing a basket across stores
 */
export function useBasketCompare(items: BasketItem[]) {
  return useQuery({
    queryKey: queryKeys.basketCompare(items),
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/staples/basket-compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items }),
      });
      if (!response.ok) throw new Error(`API Error: ${response.status}`);
      return response.json() as Promise<BasketCompareResponse>;
    },
    enabled: items.length > 0,
    staleTime: 5 * 60 * 1000,
  });
}
