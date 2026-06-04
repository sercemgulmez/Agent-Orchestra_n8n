import { Plugin } from "obsidian";
import { registerCommands } from "./commands";
import { DEFAULT_SETTINGS, normalizeSettings } from "./settings";
import { ObsidianMapView } from "./ui/map-view";
import type { ObsidianMapsSettings } from "./types";
import { MAP_VIEW_TYPE } from "./types";

export default class ObsidianMapsPlugin extends Plugin {
  settings: ObsidianMapsSettings = DEFAULT_SETTINGS;

  async onload(): Promise<void> {
    this.settings = normalizeSettings(await this.loadData());
    await this.saveData(this.settings);

    this.registerView(
      MAP_VIEW_TYPE,
      leaf => new ObsidianMapView(leaf, this.settings)
    );

    registerCommands(this);
  }

  onunload(): void {
    this.app.workspace.detachLeavesOfType(MAP_VIEW_TYPE);
  }
}
