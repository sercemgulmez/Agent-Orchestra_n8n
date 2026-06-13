export const MAP_VIEW_TYPE = "obsidian-maps-view";

export interface ObsidianMapsSettings {
  defaultZoom: number;
  markerColorProperty: string;
  markerIconProperty: string;
  customTileUrl: string;
  customTilesEnabled: boolean;
  orchestratorUrl: string;
}
