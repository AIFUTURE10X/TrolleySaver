/**
 * CategorySidebar - Vertical category navigation sidebar (Woolworths-style)
 */
import { useState, memo } from 'react';
import type { CategoryTreeItem } from '../../types';

// Category images/icons mapping
const CATEGORY_IMAGES: Record<string, string> = {
  'fruit-veg': '/categories/fruit-veg.png',
  'meat-seafood': '/categories/meat-seafood.png',
  'deli': '/categories/deli.png',
  'dairy-eggs-fridge': '/categories/dairy.png',
  'bakery': '/categories/bakery.png',
  'pantry': '/categories/pantry.png',
  'drinks': '/categories/drinks.png',
  'freezer': '/categories/freezer.png',
  'snacks-confectionery': '/categories/snacks.png',
  'international': '/categories/international.png',
  'liquor': '/categories/liquor.png',
  'beauty': '/categories/beauty.png',
  'personal-care': '/categories/personal-care.png',
  'health': '/categories/health.png',
  'cleaning-household': '/categories/cleaning.png',
  'baby': '/categories/baby.png',
  'pet': '/categories/pet.png',
};

// Fallback emoji icons
const CATEGORY_ICONS: Record<string, string> = {
  'fruit-veg': '🍎',
  'meat-seafood': '🍗',
  'deli': '🥓',
  'dairy-eggs-fridge': '🥛',
  'bakery': '🍞',
  'pantry': '🫙',
  'drinks': '🥤',
  'freezer': '❄️',
  'snacks-confectionery': '🍪',
  'international': '🌍',
  'liquor': '🍷',
  'beauty': '✨',
  'personal-care': '🧴',
  'health': '💊',
  'cleaning-household': '🧹',
  'baby': '👶',
  'pet': '🐾',
};

interface CategorySidebarProps {
  categories: CategoryTreeItem[];
  selectedCategoryId: number | null;
  onSelectCategory: (categoryId: number | null, categoryName?: string) => void;
  className?: string;
}

// Subcategory expansion panel
const SubcategoryPanel = memo(function SubcategoryPanel({
  category,
  selectedCategoryId,
  onSelect,
}: {
  category: CategoryTreeItem;
  selectedCategoryId: number | null;
  onSelect: (id: number, name: string) => void;
}) {
  if (!category.subcategories || category.subcategories.length === 0) {
    return null;
  }

  return (
    <div className="bg-gray-50 border-l-4 border-blue-500 ml-4">
      {/* View all option */}
      <button
        onClick={() => onSelect(category.id, category.name)}
        className={`w-full px-4 py-2.5 text-left text-sm flex justify-between items-center hover:bg-blue-50 transition-colors ${
          selectedCategoryId === category.id ? 'bg-blue-100 text-blue-700 font-medium' : 'text-gray-700'
        }`}
      >
        <span>All {category.name}</span>
        <span className="text-gray-400 text-xs">({category.count})</span>
      </button>

      {/* Subcategories */}
      {category.subcategories.map((sub) => (
        <button
          key={sub.id}
          onClick={() => onSelect(sub.id, sub.name)}
          className={`w-full px-4 py-2.5 text-left text-sm flex justify-between items-center hover:bg-blue-50 transition-colors ${
            selectedCategoryId === sub.id ? 'bg-blue-100 text-blue-700 font-medium' : 'text-gray-600'
          }`}
        >
          <span>{sub.name}</span>
          <span className="text-gray-400 text-xs">({sub.count})</span>
        </button>
      ))}
    </div>
  );
});

// Individual category row
const CategoryRow = memo(function CategoryRow({
  category,
  isSelected,
  isExpanded,
  selectedCategoryId,
  onSelect,
  onToggleExpand,
}: {
  category: CategoryTreeItem;
  isSelected: boolean;
  isExpanded: boolean;
  selectedCategoryId: number | null;
  onSelect: (id: number, name: string) => void;
  onToggleExpand: () => void;
}) {
  const hasSubcategories = category.subcategories && category.subcategories.length > 0;
  const icon = CATEGORY_ICONS[category.slug] || '📦';

  // Check if any subcategory is selected
  const isSubcategorySelected = category.subcategories?.some(sub => sub.id === selectedCategoryId);
  const isActive = isSelected || isSubcategorySelected;

  return (
    <div>
      <button
        onClick={() => {
          if (hasSubcategories) {
            onToggleExpand();
          } else {
            onSelect(category.id, category.name);
          }
        }}
        className={`w-full px-4 py-3 flex items-center gap-3 hover:bg-gray-50 transition-colors border-b border-gray-100 ${
          isActive ? 'bg-blue-50 border-l-4 border-l-blue-600' : ''
        }`}
      >
        {/* Icon */}
        <span className="text-2xl w-8 h-8 flex items-center justify-center flex-shrink-0">
          {icon}
        </span>

        {/* Name */}
        <span className={`flex-1 text-left text-sm ${isActive ? 'font-semibold text-blue-700' : 'text-gray-700'}`}>
          {category.name}
        </span>

        {/* Count badge */}
        <span className="text-xs text-gray-400 mr-2">
          ({category.count})
        </span>

        {/* Arrow */}
        <svg
          className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>

      {/* Expanded subcategories */}
      {isExpanded && hasSubcategories && (
        <SubcategoryPanel
          category={category}
          selectedCategoryId={selectedCategoryId}
          onSelect={onSelect}
        />
      )}
    </div>
  );
});

export function CategorySidebar({
  categories,
  selectedCategoryId,
  onSelectCategory,
  className = '',
}: CategorySidebarProps) {
  const [expandedCategory, setExpandedCategory] = useState<number | null>(null);

  const handleSelect = (id: number, name: string) => {
    onSelectCategory(id, name);
  };

  const handleToggleExpand = (categoryId: number) => {
    setExpandedCategory(expandedCategory === categoryId ? null : categoryId);
  };

  return (
    <div className={`bg-white rounded-xl border overflow-hidden ${className}`}>
      {/* Header */}
      <div className="px-4 py-3 border-b bg-gray-50">
        <h2 className="font-semibold text-gray-900">Shop by Category</h2>
      </div>

      {/* All Specials option */}
      <button
        onClick={() => onSelectCategory(null)}
        className={`w-full px-4 py-3 flex items-center gap-3 hover:bg-gray-50 transition-colors border-b border-gray-100 ${
          selectedCategoryId === null ? 'bg-blue-50 border-l-4 border-l-blue-600' : ''
        }`}
      >
        <span className="text-2xl w-8 h-8 flex items-center justify-center flex-shrink-0">
          🏠
        </span>
        <span className={`flex-1 text-left text-sm ${selectedCategoryId === null ? 'font-semibold text-blue-700' : 'text-gray-700'}`}>
          All Specials
        </span>
        <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>

      {/* Category list */}
      <div className="max-h-[calc(100vh-300px)] overflow-y-auto">
        {categories.map((category) => (
          <CategoryRow
            key={category.id}
            category={category}
            isSelected={selectedCategoryId === category.id}
            isExpanded={expandedCategory === category.id}
            selectedCategoryId={selectedCategoryId}
            onSelect={handleSelect}
            onToggleExpand={() => handleToggleExpand(category.id)}
          />
        ))}
      </div>
    </div>
  );
}
