import { useBasketCompare } from '../api/hooks';
import type { BasketItem, BasketStoreTotal } from '../types';

interface BasketItemDisplay extends BasketItem {
  product_name: string;
}

interface StaplesBasketProps {
  items: BasketItemDisplay[];
  onRemoveItem: (productId: number) => void;
  onUpdateQuantity: (productId: number, quantity: number) => void;
  onIncrementQuantity: (productId: number) => void;
  onDecrementQuantity: (productId: number) => void;
  onClearBasket: () => void;
  isOpen: boolean;
  onClose: () => void;
}

const STORE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  woolworths: { bg: 'bg-[#00A651]/10', text: 'text-[#00A651]', border: 'border-[#00A651]' },
  coles: { bg: 'bg-[#E01A22]/10', text: 'text-[#E01A22]', border: 'border-[#E01A22]' },
  aldi: { bg: 'bg-[#00448C]/10', text: 'text-[#00448C]', border: 'border-[#00448C]' },
  iga: { bg: 'bg-[#FF6B00]/10', text: 'text-[#FF6B00]', border: 'border-[#FF6B00]' },
};

function StoreTotalRow({ storeTotal, isBest }: { storeTotal: BasketStoreTotal; isBest: boolean }) {
  const colors = STORE_COLORS[storeTotal.store_slug] || STORE_COLORS.woolworths;
  const hasAllItems = storeTotal.items_missing.length === 0;

  return (
    <div
      className={`flex items-center justify-between p-3 rounded-lg ${
        isBest ? colors.bg + ' border-2 ' + colors.border : 'bg-gray-50'
      }`}
    >
      <div className="flex items-center gap-2">
        <span className={`w-3 h-3 rounded-full ${colors.text.replace('text-', 'bg-')}`} />
        <div>
          <span className={`font-medium ${isBest ? colors.text : 'text-gray-700'}`}>
            {storeTotal.store_name}
          </span>
          {!hasAllItems && (
            <span className="text-xs text-gray-400 ml-2">
              ({storeTotal.items_available}/{storeTotal.items_available + storeTotal.items_missing.length} items)
            </span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className={`font-bold text-lg ${isBest ? colors.text : 'text-gray-900'}`}>
          {storeTotal.total}
        </span>
        {isBest && <span className="text-yellow-500">★ CHEAPEST</span>}
      </div>
    </div>
  );
}

export function StaplesBasket({
  items,
  onRemoveItem,
  onIncrementQuantity,
  onDecrementQuantity,
  onClearBasket,
  isOpen,
  onClose,
}: StaplesBasketProps) {
  const { data: comparison, isLoading } = useBasketCompare(
    items.map((item) => ({
      product_id: item.product_id,
      product_name: item.product_name,
      quantity: item.quantity,
    }))
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Panel */}
      <div className="absolute right-0 top-0 h-full w-full max-w-md bg-white shadow-xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">
            Your Basket ({items.length} items)
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
          >
            &times;
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {items.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <p className="text-4xl mb-4">🛒</p>
              <p>Your basket is empty</p>
              <p className="text-sm mt-2">Add products to compare prices across stores</p>
            </div>
          ) : (
            <div className="p-4 space-y-4">
              {/* Basket Items */}
              <div className="space-y-2">
                {items.map((item) => (
                  <div
                    key={item.product_id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {item.product_name}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 ml-4">
                      <button
                        onClick={() => onDecrementQuantity(item.product_id)}
                        className="w-7 h-7 rounded-full bg-gray-200 hover:bg-gray-300 text-gray-600 flex items-center justify-center text-lg"
                      >
                        -
                      </button>
                      <span className="w-8 text-center font-medium">{item.quantity}</span>
                      <button
                        onClick={() => onIncrementQuantity(item.product_id)}
                        className="w-7 h-7 rounded-full bg-gray-200 hover:bg-gray-300 text-gray-600 flex items-center justify-center text-lg"
                      >
                        +
                      </button>
                      <button
                        onClick={() => onRemoveItem(item.product_id)}
                        className="ml-2 text-red-500 hover:text-red-600 text-sm"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Store Totals */}
              {isLoading ? (
                <div className="p-4 text-center text-gray-500">
                  Calculating totals...
                </div>
              ) : comparison ? (
                <div className="mt-6">
                  <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
                    Store Totals
                  </h3>
                  <div className="space-y-2">
                    {comparison.basket_totals.map((storeTotal) => (
                      <StoreTotalRow
                        key={storeTotal.store_id}
                        storeTotal={storeTotal}
                        isBest={storeTotal.store_name === comparison.best_store}
                      />
                    ))}
                  </div>

                  {/* Savings Summary */}
                  {comparison.savings_vs_worst && (
                    <div className="mt-4 p-4 bg-green-50 rounded-lg border border-green-200">
                      <div className="flex items-center gap-2">
                        <span className="text-2xl">💰</span>
                        <div>
                          <p className="text-green-700 font-semibold">
                            {comparison.savings_vs_worst}
                          </p>
                          <p className="text-sm text-green-600">
                            Shop at {comparison.best_store} for the best deal
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          )}
        </div>

        {/* Footer */}
        {items.length > 0 && (
          <div className="p-4 border-t bg-gray-50">
            <button
              onClick={onClearBasket}
              className="w-full py-2 px-4 text-sm font-medium text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors"
            >
              Clear Basket
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// Floating basket button component
interface BasketButtonProps {
  itemCount: number;
  onClick: () => void;
}

export function BasketButton({ itemCount, onClick }: BasketButtonProps) {
  return (
    <button
      onClick={onClick}
      className="fixed bottom-6 right-6 bg-gray-900 text-white p-4 rounded-full shadow-lg hover:bg-gray-800 transition-colors z-40"
    >
      <div className="relative">
        <svg
          className="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"
          />
        </svg>
        {itemCount > 0 && (
          <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs font-bold w-5 h-5 rounded-full flex items-center justify-center">
            {itemCount}
          </span>
        )}
      </div>
    </button>
  );
}
