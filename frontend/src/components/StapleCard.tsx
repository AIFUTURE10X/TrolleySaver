import type { StapleProduct, StapleStorePrice } from '../types';

interface StapleCardProps {
  product: StapleProduct;
  onAddToBasket?: (product: StapleProduct) => void;
  isInBasket?: boolean;
}

const STORE_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  woolworths: { bg: 'bg-[#00A651]/10', text: 'text-[#00A651]', dot: 'bg-[#00A651]' },
  coles: { bg: 'bg-[#E01A22]/10', text: 'text-[#E01A22]', dot: 'bg-[#E01A22]' },
  aldi: { bg: 'bg-[#00448C]/10', text: 'text-[#00448C]', dot: 'bg-[#00448C]' },
  iga: { bg: 'bg-[#FF6B00]/10', text: 'text-[#FF6B00]', dot: 'bg-[#FF6B00]' },
};

function StorePriceRow({ storePrice, isBest }: { storePrice: StapleStorePrice; isBest: boolean }) {
  const colors = STORE_COLORS[storePrice.store_slug] || STORE_COLORS.woolworths;

  return (
    <div className={`flex items-center justify-between py-1.5 px-2 rounded ${isBest ? colors.bg : ''}`}>
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${colors.dot}`} />
        <span className={`text-sm ${isBest ? 'font-semibold' : 'text-gray-600'}`}>
          {storePrice.store_name}
        </span>
      </div>
      <div className="flex items-center gap-1.5">
        <span className={`font-semibold ${isBest ? colors.text : 'text-gray-900'}`}>
          {storePrice.price}
        </span>
        {isBest && (
          <span className="text-yellow-500 text-sm">★</span>
        )}
      </div>
    </div>
  );
}

export function StapleCard({ product, onAddToBasket, isInBasket }: StapleCardProps) {
  const bestPrice = product.best_price;
  const savingsDisplay = product.savings_amount
    ? `$${(product.savings_amount / 100).toFixed(2)}`
    : null;

  return (
    <div className="bg-white rounded-xl shadow-sm border hover:shadow-md transition-all overflow-hidden">
      {/* Product Image */}
      <div className="relative aspect-square bg-gray-50 p-4 flex items-center justify-center">
        <img
          src={product.image_url || '/placeholder-product.svg'}
          alt={product.name}
          className="max-h-full max-w-full object-contain"
          onError={(e) => {
            (e.target as HTMLImageElement).src = '/placeholder-product.svg';
          }}
        />

        {/* Category Badge */}
        <div className="absolute top-2 left-2">
          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full">
            {product.category_display}
          </span>
        </div>

        {/* Savings Badge */}
        {savingsDisplay && (
          <div className="absolute top-2 right-2">
            <span className="text-xs bg-green-500 text-white px-2 py-1 rounded-full font-medium">
              Save up to {savingsDisplay}
            </span>
          </div>
        )}
      </div>

      {/* Product Details */}
      <div className="p-4 border-t">
        {/* Product Name */}
        <h3 className="font-semibold text-gray-900 line-clamp-2 min-h-[2.5rem]">
          {product.name}
        </h3>

        {/* Unit */}
        {product.unit && (
          <span className="inline-block mt-1 text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
            {product.unit}
          </span>
        )}

        {/* Store Prices */}
        <div className="mt-3 space-y-0.5">
          {product.prices.map((storePrice) => (
            <StorePriceRow
              key={storePrice.store_id}
              storePrice={storePrice}
              isBest={bestPrice?.store_id === storePrice.store_id}
            />
          ))}
        </div>

        {/* Best Price Summary */}
        {bestPrice && (
          <div className="mt-3 pt-3 border-t">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">Best at</span>
              <span className="font-semibold text-green-600">
                {bestPrice.store_name}
              </span>
            </div>
            {product.price_range && (
              <div className="text-xs text-gray-400 mt-1">
                Range: {product.price_range}
              </div>
            )}
          </div>
        )}

        {/* Add to Basket Button */}
        {onAddToBasket && (
          <button
            onClick={() => onAddToBasket(product)}
            className={`mt-3 w-full py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
              isInBasket
                ? 'bg-green-100 text-green-700 hover:bg-green-200'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {isInBasket ? '✓ In Basket' : '+ Add to Basket'}
          </button>
        )}
      </div>
    </div>
  );
}
