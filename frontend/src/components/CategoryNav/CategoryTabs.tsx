/**
 * CategoryTabs - Horizontal scrollable category navigation with dropdown subcategories
 */
import { useState, memo, useRef, useEffect, useLayoutEffect } from 'react';
import { createPortal } from 'react-dom';
import type { CategoryTreeItem } from '../../types';

// Icon mapping for categories (using emoji as fallback)
const CATEGORY_ICONS: Record<string, string> = {
  apple: '🍎',
  drumstick: '🍗',
  bacon: '🥓',
  milk: '🥛',
  'bread-slice': '🍞',
  jar: '🫙',
  'glass-water': '🥤',
  snowflake: '❄️',
  cookie: '🍪',
  globe: '🌍',
  'wine-glass': '🍷',
  sparkles: '✨',
  'hand-sparkles': '🧴',
  'heart-pulse': '💊',
  'spray-can': '🧹',
  baby: '👶',
  paw: '🐾',
};

interface CategoryTabsProps {
  categories: CategoryTreeItem[];
  selectedCategoryId: number | null;
  onSelectCategory: (categoryId: number | null, categoryName?: string) => void;
  totalCount?: number;
}

// Subcategory dropdown menu - uses portal to escape overflow clipping
const SubcategoryDropdown = memo(function SubcategoryDropdown({
  category,
  onSelect,
  onClose,
  anchorRef,
}: {
  category: CategoryTreeItem;
  onSelect: (id: number, name: string) => void;
  onClose: () => void;
  anchorRef: React.RefObject<HTMLButtonElement | null>;
}) {
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ top: 0, left: 0 });

  // Calculate position based on anchor element (fixed positioning = viewport-relative)
  useLayoutEffect(() => {
    if (anchorRef.current) {
      const rect = anchorRef.current.getBoundingClientRect();
      setPosition({
        top: rect.bottom + 4,
        left: rect.left,
      });
    }
  }, [anchorRef]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        anchorRef.current &&
        !anchorRef.current.contains(event.target as Node)
      ) {
        onClose();
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose, anchorRef]);

  if (!category.subcategories || category.subcategories.length === 0) {
    return null;
  }

  return createPortal(
    <div
      ref={dropdownRef}
      className="fixed bg-white rounded-lg shadow-lg border py-2 min-w-[200px] z-50"
      style={{ top: position.top, left: position.left }}
    >
      {/* View all in this category */}
      <button
        onClick={() => {
          onSelect(category.id, category.name);
          onClose();
        }}
        className="w-full px-4 py-2 text-left text-sm font-medium text-blue-600 hover:bg-blue-50 border-b"
      >
        All {category.name} ({category.count})
      </button>

      {/* Subcategories */}
      {category.subcategories.map((sub) => (
        <button
          key={sub.id}
          onClick={() => {
            onSelect(sub.id, sub.name);
            onClose();
          }}
          className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex justify-between items-center"
        >
          <span>{sub.name}</span>
          <span className="text-gray-400 text-xs">{sub.count}</span>
        </button>
      ))}
    </div>,
    document.body
  );
});

// Individual category tab button
const CategoryTab = memo(function CategoryTab({
  category,
  isSelected,
  onClick,
  onDropdownToggle,
  showDropdown,
  onSelectSubcategory,
}: {
  category?: CategoryTreeItem;
  isSelected: boolean;
  onClick: () => void;
  onDropdownToggle?: () => void;
  showDropdown?: boolean;
  onSelectSubcategory?: (id: number, name: string) => void;
}) {
  const buttonRef = useRef<HTMLButtonElement>(null);
  const icon = category?.icon ? CATEGORY_ICONS[category.icon] || '📦' : '🏠';
  const name = category?.name || 'All';
  const count = category?.count;
  const hasSubcategories = category?.subcategories && category.subcategories.length > 0;

  return (
    <div className="relative flex-shrink-0">
      <button
        ref={buttonRef}
        onClick={onClick}
        className={`flex items-center gap-2 px-4 py-2.5 rounded-full font-medium text-sm transition-all whitespace-nowrap ${
          isSelected
            ? 'bg-blue-600 text-white shadow-md'
            : 'bg-white text-gray-600 hover:bg-gray-100 border'
        }`}
      >
        <span className="text-base">{icon}</span>
        <span>{name}</span>
        {count !== undefined && (
          <span className={`text-xs ${isSelected ? 'text-blue-200' : 'text-gray-400'}`}>
            ({count})
          </span>
        )}
        {hasSubcategories && (
          <span
            role="button"
            tabIndex={0}
            onClick={(e) => {
              e.stopPropagation();
              onDropdownToggle?.();
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.stopPropagation();
                onDropdownToggle?.();
              }
            }}
            className={`ml-1 p-0.5 rounded hover:bg-white/20 cursor-pointer ${isSelected ? 'text-blue-200' : 'text-gray-400'}`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </span>
        )}
      </button>

      {/* Dropdown - rendered via portal */}
      {showDropdown && category && onSelectSubcategory && (
        <SubcategoryDropdown
          category={category}
          onSelect={onSelectSubcategory}
          onClose={() => onDropdownToggle?.()}
          anchorRef={buttonRef}
        />
      )}
    </div>
  );
});

export function CategoryTabs({
  categories,
  selectedCategoryId,
  onSelectCategory,
}: CategoryTabsProps) {
  const [openDropdown, setOpenDropdown] = useState<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const handleTabClick = (categoryId: number | null, categoryName?: string) => {
    onSelectCategory(categoryId, categoryName);
    setOpenDropdown(null);
  };

  const handleDropdownToggle = (categoryId: number) => {
    setOpenDropdown(openDropdown === categoryId ? null : categoryId);
  };

  const handleSelectSubcategory = (id: number, name: string) => {
    onSelectCategory(id, name);
    setOpenDropdown(null);
  };

  // Scroll buttons for overflow
  const scrollLeft = () => {
    scrollRef.current?.scrollBy({ left: -200, behavior: 'smooth' });
  };

  const scrollRight = () => {
    scrollRef.current?.scrollBy({ left: 200, behavior: 'smooth' });
  };

  return (
    <div className="relative pb-2">
      {/* Scroll left button */}
      <button
        onClick={scrollLeft}
        className="absolute left-0 top-1/2 -translate-y-1/2 z-10 bg-white/90 hover:bg-white shadow-md rounded-full p-1.5 hidden md:block"
      >
        <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      {/* Scrollable tabs container */}
      <div
        ref={scrollRef}
        className="flex gap-2 overflow-x-auto scrollbar-hide py-2 px-1 md:px-8"
        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
      >
        {/* All categories tab */}
        <CategoryTab
          isSelected={selectedCategoryId === null}
          onClick={() => handleTabClick(null)}
        />

        {/* Category tabs */}
        {categories.map((category) => (
          <CategoryTab
            key={category.id}
            category={category}
            isSelected={selectedCategoryId === category.id}
            onClick={() => handleTabClick(category.id, category.name)}
            onDropdownToggle={() => handleDropdownToggle(category.id)}
            showDropdown={openDropdown === category.id}
            onSelectSubcategory={handleSelectSubcategory}
          />
        ))}
      </div>

      {/* Scroll right button */}
      <button
        onClick={scrollRight}
        className="absolute right-0 top-1/2 -translate-y-1/2 z-10 bg-white/90 hover:bg-white shadow-md rounded-full p-1.5 hidden md:block"
      >
        <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </div>
  );
}
