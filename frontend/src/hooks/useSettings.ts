import { useEffect } from "react";
import { useSettingsStore } from "../stores/settingsStore";

export function useSettings() {
  const settings = useSettingsStore((state) => state.settings);
  const loading = useSettingsStore((state) => state.loading);
  const error = useSettingsStore((state) => state.error);
  const fetchSettings = useSettingsStore((state) => state.fetchSettings);
  const patchSettings = useSettingsStore((state) => state.patchSettings);

  useEffect(() => {
    if (!settings && !loading && !error) {
      void fetchSettings();
    }
  }, [settings, loading, error, fetchSettings]);

  return { settings, loading, error, patchSettings, fetchSettings };
}
