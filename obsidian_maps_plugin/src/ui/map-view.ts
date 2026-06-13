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
    return "Token Flow Graph";
  }

  getIcon(): string {
    return "git-branch";
  }

  async onOpen(): Promise<void> {
    const container = this.containerEl.children[1] as HTMLElement;
    container.empty();
    container.style.cssText = "padding:0;margin:0;height:100%;overflow:hidden;";

    const orchestratorUrl = this.settings.orchestratorUrl || "http://localhost:8000";

    const wrapper = container.createDiv();
    wrapper.style.cssText = "position:relative;width:100%;height:100%;";

    const iframe = wrapper.createEl("iframe");
    iframe.setAttribute("src", `${orchestratorUrl}/graph`);
    iframe.setAttribute("title", "YemekTest Token Flow Graph");
    iframe.style.cssText = "width:100%;height:100%;border:none;display:block;";

    // Overlay shown while iframe loads
    const overlay = wrapper.createDiv();
    overlay.style.cssText = [
      "position:absolute;inset:0;",
      "display:flex;flex-direction:column;align-items:center;justify-content:center;",
      "background:#0d1117;color:#8b949e;font-size:13px;gap:8px;",
      "pointer-events:none;transition:opacity 0.3s;",
    ].join("");
    overlay.createEl("div", { text: "Loading graph…" });

    const hint = overlay.createEl("div");
    hint.style.cssText = "font-size:11px;opacity:0.6;";
    hint.setText(`Connecting to ${orchestratorUrl}`);

    iframe.addEventListener("load", () => {
      overlay.style.opacity = "0";
      setTimeout(() => overlay.remove(), 300);
    });

    iframe.addEventListener("error", () => {
      overlay.innerHTML = "";
      const msg = overlay.createEl("div");
      msg.style.color = "#ff6b6b";
      msg.setText(`Cannot reach orchestrator at ${orchestratorUrl}`);
      const sub = overlay.createEl("div");
      sub.style.cssText = "font-size:11px;opacity:0.6;margin-top:4px;";
      sub.setText("Check Settings → Obsidian Maps → Orchestrator URL");
      overlay.style.opacity = "1";
      overlay.style.pointerEvents = "auto";
    });
  }

  async onClose(): Promise<void> {
    const container = this.containerEl.children[1] as HTMLElement;
    container.empty();
  }
}
