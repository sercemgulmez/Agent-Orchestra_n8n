import { ItemView, WorkspaceLeaf } from "obsidian";
import type { ObsidianMapsSettings } from "../types";
import { MAP_VIEW_TYPE } from "../types";

export class ObsidianMapView extends ItemView {
  private settings: ObsidianMapsSettings;

  constructor(leaf: WorkspaceLeaf, settings: ObsidianMapsSettings) {
    super(leaf);
    this.settings = settings;
  }

  getViewType(): string {
    return MAP_VIEW_TYPE;
  }

  getDisplayText(): string {
    return "Map view";
  }

  async onOpen(): Promise<void> {
    const container = this.containerEl.children[1];
    container.empty();
    container.createEl("h2", { text: "Map view" });
    container.createEl("p", {
      text: `Default zoom: ${this.settings.defaultZoom}. Marker properties: ${this.settings.markerColorProperty}, ${this.settings.markerIconProperty}.`
    });
    container.createEl("p", {
      text: this.settings.customTilesEnabled
        ? "Custom tiles are enabled by user setting."
        : "Custom tiles are disabled. The view stays local-first by default."
    });
  }

  async onClose(): Promise<void> {
    this.containerEl.children[1].empty();
  }
}
