// Hand-written child handling. The generated comp.ts delegates its three child
// hooks here; the spec records why.

// Each child is assigned to the next tab in order, so the position is state and
// no rule can express it.
export const manualChildren = {
  insertBefore(child, beforeChild) {},
  appendInitialChild(child) {
    this.appendChild(child);
  },
  appendChild(child) {
    this.setTab(this.tabs[this.currentAppendIndex] || "", child);
    this.currentAppendIndex++;
  },
};
