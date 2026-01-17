import { useState, useEffect, useCallback } from 'react';
import type { BasketItem } from '../types';

const BASKET_STORAGE_KEY = 'staples-basket';

interface BasketItemWithName extends BasketItem {
  product_name: string;
}

export function useStaplesBasket() {
  const [items, setItems] = useState<BasketItemWithName[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load basket from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(BASKET_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          setItems(parsed);
        }
      }
    } catch (e) {
      console.error('Error loading basket from localStorage:', e);
    }
    setIsLoaded(true);
  }, []);

  // Save basket to localStorage whenever it changes
  useEffect(() => {
    if (isLoaded) {
      try {
        localStorage.setItem(BASKET_STORAGE_KEY, JSON.stringify(items));
      } catch (e) {
        console.error('Error saving basket to localStorage:', e);
      }
    }
  }, [items, isLoaded]);

  const addItem = useCallback((productId: number, productName: string) => {
    setItems((prev) => {
      const existing = prev.find((item) => item.product_id === productId);
      if (existing) {
        // Increment quantity
        return prev.map((item) =>
          item.product_id === productId
            ? { ...item, quantity: item.quantity + 1 }
            : item
        );
      }
      // Add new item
      return [...prev, { product_id: productId, product_name: productName, quantity: 1 }];
    });
  }, []);

  const removeItem = useCallback((productId: number) => {
    setItems((prev) => prev.filter((item) => item.product_id !== productId));
  }, []);

  const updateQuantity = useCallback((productId: number, quantity: number) => {
    if (quantity <= 0) {
      removeItem(productId);
      return;
    }
    setItems((prev) =>
      prev.map((item) =>
        item.product_id === productId ? { ...item, quantity } : item
      )
    );
  }, [removeItem]);

  const incrementQuantity = useCallback((productId: number) => {
    setItems((prev) =>
      prev.map((item) =>
        item.product_id === productId
          ? { ...item, quantity: item.quantity + 1 }
          : item
      )
    );
  }, []);

  const decrementQuantity = useCallback((productId: number) => {
    setItems((prev) => {
      const item = prev.find((i) => i.product_id === productId);
      if (item && item.quantity <= 1) {
        return prev.filter((i) => i.product_id !== productId);
      }
      return prev.map((i) =>
        i.product_id === productId ? { ...i, quantity: i.quantity - 1 } : i
      );
    });
  }, []);

  const clearBasket = useCallback(() => {
    setItems([]);
  }, []);

  const isInBasket = useCallback(
    (productId: number) => items.some((item) => item.product_id === productId),
    [items]
  );

  const getQuantity = useCallback(
    (productId: number) => {
      const item = items.find((i) => i.product_id === productId);
      return item?.quantity || 0;
    },
    [items]
  );

  const totalItems = items.reduce((sum, item) => sum + item.quantity, 0);

  return {
    items,
    isLoaded,
    addItem,
    removeItem,
    updateQuantity,
    incrementQuantity,
    decrementQuantity,
    clearBasket,
    isInBasket,
    getQuantity,
    totalItems,
  };
}
