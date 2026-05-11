"use client";

import { useCallback, useEffect, useState } from "react";

const KEY = "dantadanta_favorites";

export interface FavoriteItem {
  symbol: string;
  name: string;
  market: string;
}

export function useFavorites() {
  const [favorites, setFavorites] = useState<FavoriteItem[]>([]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) setFavorites(JSON.parse(raw));
    } catch {}
  }, []);

  const save = (next: FavoriteItem[]) => {
    setFavorites(next);
    localStorage.setItem(KEY, JSON.stringify(next));
  };

  const toggle = useCallback((item: FavoriteItem) => {
    setFavorites((prev) => {
      const exists = prev.some((f) => f.symbol === item.symbol);
      const next = exists
        ? prev.filter((f) => f.symbol !== item.symbol)
        : [...prev, item];
      localStorage.setItem(KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const isFavorite = useCallback(
    (symbol: string) => favorites.some((f) => f.symbol === symbol),
    [favorites]
  );

  return { favorites, toggle, isFavorite };
}
