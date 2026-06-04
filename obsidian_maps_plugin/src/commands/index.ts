import { Notice, Plugin } from "obsidian";
import { MAP_VIEW_TYPE } from "../types";

export function registerCommands(plugin: Plugin): void {
  plugin.addCommand({
    id: "open-map-view",
    name: "Open map view",
    callback: async () => {
      const leaf = plugin.app.workspace.getLeaf(true);
      await leaf.setViewState({ type: MAP_VIEW_TYPE, active: true });
      plugin.app.workspace.revealLeaf(leaf);
      new Notice("Map view opened");
    }
  });
}
