import { Plugin, PluginSettingTab, Setting, App } from "obsidian";
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

    this.addSettingTab(new ObsidianMapsSettingTab(this.app, this));

    registerCommands(this);
  }

  onunload(): void {
    this.app.workspace.detachLeavesOfType(MAP_VIEW_TYPE);
  }
}

class ObsidianMapsSettingTab extends PluginSettingTab {
  plugin: ObsidianMapsPlugin;

  constructor(app: App, plugin: ObsidianMapsPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl("h2", { text: "Obsidian Maps Settings" });

    new Setting(containerEl)
      .setName("Orchestrator URL")
      .setDesc("Base URL of the YemekTest Orchestrator (used for the Token Flow Graph view).")
      .addText(text => text
        .setPlaceholder("http://localhost:8000")
        .setValue(this.plugin.settings.orchestratorUrl)
        .onChange(async value => {
          this.plugin.settings.orchestratorUrl = value.trim() || "http://localhost:8000";
          await this.plugin.saveData(this.plugin.settings);
        })
      );

    new Setting(containerEl)
      .setName("Default zoom")
      .setDesc("Initial zoom level for map views (1–20).")
      .addSlider(sl => sl
        .setLimits(1, 20, 1)
        .setValue(this.plugin.settings.defaultZoom)
        .setDynamicTooltip()
        .onChange(async value => {
          this.plugin.settings.defaultZoom = value;
          await this.plugin.saveData(this.plugin.settings);
        })
      );

    new Setting(containerEl)
      .setName("Marker color property")
      .setDesc("Front-matter key used to set marker color.")
      .addText(text => text
        .setValue(this.plugin.settings.markerColorProperty)
        .onChange(async value => {
          this.plugin.settings.markerColorProperty = value;
          await this.plugin.saveData(this.plugin.settings);
        })
      );

    new Setting(containerEl)
      .setName("Marker icon property")
      .setDesc("Front-matter key used to set marker icon.")
      .addText(text => text
        .setValue(this.plugin.settings.markerIconProperty)
        .onChange(async value => {
          this.plugin.settings.markerIconProperty = value;
          await this.plugin.saveData(this.plugin.settings);
        })
      );

    new Setting(containerEl)
      .setName("Custom tile URL")
      .setDesc("Leave blank to stay local-first (default). Requires explicit opt-in.")
      .addText(text => text
        .setPlaceholder("https://tile.example.com/{z}/{x}/{y}.png")
        .setValue(this.plugin.settings.customTileUrl)
        .onChange(async value => {
          this.plugin.settings.customTileUrl = value.trim();
          await this.plugin.saveData(this.plugin.settings);
        })
      );
  }
}
