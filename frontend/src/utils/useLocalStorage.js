import { useState, useEffect } from 'react';

/**
 * Custom React hook to sync state seamlessly with localStorage.
 * Automatically restores values upon page reload (F5) and updates storage on change.
 */
export function useLocalStorage(key, defaultValue) {
  const [value, setValue] = useState(() => {
    try {
      const saved = localStorage.getItem(key);
      if (saved !== null) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.warn(`Lỗi khi đọc cache localStorage cho key "${key}":`, e);
    }
    return defaultValue;
  });

  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
      console.warn(`Lỗi khi lưu cache localStorage cho key "${key}":`, e);
    }
  }, [key, value]);

  return [value, setValue];
}
