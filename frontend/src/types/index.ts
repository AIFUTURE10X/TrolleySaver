export interface Store {
  id: number;
  name: string;
  slug: string;
  specials_day: string;
}

export interface Special {
  id: number;
  name: string;
  brand?: string | null;
  size?: string | null;
  category?: string | null;
  price: string;
  was_price?: string | null;
  discount_percent?: number | null;
  unit_price?: string | null;
  store_product_id?: string | null;
  product_url?: string | null;
  image_url?: string | null;
  valid_from?: string | null;
  valid_to?: string | null;
  store_id: number;
  store_name?: string | null;
  store_slug?: string | null;
  scraped_at?: string | null;
  created_at?: string | null;
}

export interface SpecialsList {
  items: Special[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

export interface SpecialsStats {
  total_specials: number;
  by_store: Record<string, number>;
  half_price_count: number;
  last_updated?: string | null;
}

export interface CategoryCount {
  name: string;
  count: number;
}

// Category tree types for hierarchical navigation
export interface SubcategoryItem {
  id: number;
  name: string;
  slug: string;
  count: number;
}

export interface CategoryTreeItem {
  id: number;
  name: string;
  slug: string;
  icon: string | null;
  count: number;
  subcategories: SubcategoryItem[];
}

export interface CategoryTreeResponse {
  categories: CategoryTreeItem[];
  total_categorized: number;
  total_uncategorized: number;
}

// Comparison types
export interface SpecialStorePrice {
  special_id: number;
  store_id: number;
  store_name: string;
  store_slug: string;
  price: string;
  was_price: string | null;
  discount_percent: number | null;
  unit_price: string | null;
  image_url: string | null;
  product_url: string | null;
  valid_to: string | null;
}

export interface BrandMatchResult {
  product_name: string;
  brand: string | null;
  size: string | null;
  stores: SpecialStorePrice[];
  cheapest_store: string | null;
  price_spread: string | null;
  savings_potential: string | null;
}

export interface TypeMatchResult {
  product_type: string;
  category_id: number | null;
  category_name: string | null;
  reference_product: SpecialStorePrice;
  similar_products: SpecialStorePrice[];
  cheapest_option: string | null;
  cheapest_price: string | null;
  total_options: number;
}

// Fresh Foods types
export interface FreshFoodStorePrice {
  store_id: number;
  store_name: string;
  store_slug: string;
  price: string;
  unit_price: string | null;
  image_url: string | null;
  product_url: string | null;
}

export interface FreshFoodItem {
  product_id: number;
  product_name: string;
  brand: string | null;
  size: string | null;
  category: 'produce' | 'meat';
  stores: FreshFoodStorePrice[];
  cheapest_store: string | null;
  cheapest_price: string | null;
  price_range: string | null;
}

export interface FreshFoodsResponse {
  produce: FreshFoodItem[];
  meat: FreshFoodItem[];
  total_products: number;
  last_updated: string | null;
}
