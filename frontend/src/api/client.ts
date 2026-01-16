import type {
  Store,
  Special,
  SpecialsList,
  SpecialsStats,
  CategoryCount,
} from '../types';

const API_BASE = '/api';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

// Stores
export async function getStores(): Promise<Store[]> {
  return fetchJson<Store[]>('/stores');
}

// Specials API
export async function getSpecials(params?: {
  store?: string;
  category?: string;
  min_discount?: number;
  search?: string;
  sort?: 'discount' | 'price' | 'name';
  page?: number;
  limit?: number;
}): Promise<SpecialsList> {
  const searchParams = new URLSearchParams();
  if (params?.store) searchParams.set('store', params.store);
  if (params?.category) searchParams.set('category', params.category);
  if (params?.min_discount) searchParams.set('min_discount', String(params.min_discount));
  if (params?.search) searchParams.set('search', params.search);
  if (params?.sort) searchParams.set('sort', params.sort);
  if (params?.page) searchParams.set('page', String(params.page));
  if (params?.limit) searchParams.set('limit', String(params.limit));

  const query = searchParams.toString();
  return fetchJson<SpecialsList>(`/specials${query ? `?${query}` : ''}`);
}

export async function getSpecialsStats(): Promise<SpecialsStats> {
  return fetchJson<SpecialsStats>('/specials/stats');
}

export async function getSpecialsCategories(): Promise<CategoryCount[]> {
  return fetchJson<CategoryCount[]>('/specials/categories');
}

export async function getSpecial(id: number): Promise<Special> {
  return fetchJson<Special>(`/specials/${id}`);
}
