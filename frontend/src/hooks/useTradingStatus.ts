import { useEffect } from "react";
import { usePermissionsStore } from "../stores/permissionsStore";

export function useTradingStatus() {
  const permissions = usePermissionsStore((state) => state.permissions);
  const tradingStatus = usePermissionsStore((state) => state.tradingStatus);
  const loading = usePermissionsStore((state) => state.loading);
  const error = usePermissionsStore((state) => state.error);
  const fetchAll = usePermissionsStore((state) => state.fetchAll);
  const updateLevel = usePermissionsStore((state) => state.updateLevel);

  useEffect(() => {
    if (!permissions && !tradingStatus && !loading && !error) {
      void fetchAll();
    }
  }, [permissions, tradingStatus, loading, error, fetchAll]);

  return { permissions, tradingStatus, loading, error, updateLevel, refresh: fetchAll };
}
