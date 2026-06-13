import type { ObsidianMapsSettings } from "./types";

export const DEFAULT_SETTINGS: ObsidianMapsSettings = {
  defaultZoom: 8,
  markerColorProperty: "mapColor",
  markerIconProperty: "mapIcon",
  customTileUrl: "",
  customTilesEnabled: false,
  orchestratorUrl: "http://localhost:8000",
};

export function normalizeSettings(data: Partial<ObsidianMapsSettings> | null | undefined): ObsidianMapsSettings {
  const merged = Object.assign({}, DEFAULT_SETTINGS, data ?? {});
  return {
    defaultZoom: Math.max(1, Math.min(20, Number(merged.defaultZoom) || DEFAULT_SETTINGS.defaultZoom)),
    markerColorProperty: String(merged.markerColorProperty || DEFAULT_SETTINGS.markerColorProperty),
    markerIconProperty: String(merged.markerIconProperty || DEFAULT_SETTINGS.markerIconProperty),
    customTileUrl: String(merged.customTileUrl || ""),
    customTilesEnabled: Boolean(merged.customTilesEnabled && merged.customTileUrl),
    orchestratorUrl: String(merged.orchestratorUrl || DEFAULT_SETTINGS.orchestratorUrl),
  };
}
