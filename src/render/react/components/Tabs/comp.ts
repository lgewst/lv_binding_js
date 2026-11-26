// Generated from scripts/data/widgets_manifest.json. Do not edit by hand.
// Regenerate with: python3 autogen/ts_emitter.py
import { LV_DIR_MAP } from "../../core/lv_types";
import { CommonComponentApi, CommonProps } from "../common/index";
import {
  EVENTTYPE_MAP,
  STYLE_TYPE,
  handleEvent,
  setStyle,
  styleGetterProp,
  applyDataPropsToDataset,
} from "../config";

import { GetBridge } from "../../core/bridge";
import { manualChildren } from "./manual";

const bridge = GetBridge();
const NativeComp = bridge.NativeRender.NativeComponents.TabView;

const tabPositionObj = {
  left: LV_DIR_MAP.left,
  top: LV_DIR_MAP.top,
  right: LV_DIR_MAP.right,
  bottom: LV_DIR_MAP.bottom,
};

export type TabsProps = CommonProps & {
  tabPosition: "left" | "top" | "right" | "bottom";
  tabSize?: number;
  tabs: string[];
};

function setTabsProps(comp, newProps: TabsProps, oldProps: Partial<TabsProps>) {
  const setter = {
    ...CommonComponentApi({ compName: "Tabs", comp, newProps, oldProps }),

  };
  Object.keys(setter).forEach((key) => {
    if (newProps.hasOwnProperty(key)) {
      setter[key](newProps[key]);
    }
  });
  applyDataPropsToDataset(comp, newProps);
}

export class TabsComp extends NativeComp {
  constructor({ uid, tabPosition, tabSize = 0 }) {
    tabPosition = tabPositionObj[tabPosition] || tabPositionObj.top;
    super({ uid, tabPosition, tabSize });
    this.uid = uid;

    const style = super.style;
    const that = this;
    this.style = new Proxy(this, {
      get(obj, prop) {
        if (styleGetterProp.includes(prop)) {
          return style[prop].call(that);
        }
      },
    });
    this.currentAppendIndex = 0;
  }
  setProps(newProps: TabsProps, oldProps: Partial<TabsProps>) {
    this.tabs = newProps.tabs;
    setTabsProps(this, newProps, oldProps);
  }
  insertBefore(child, beforeChild) {
    manualChildren.insertBefore.call(this, child, beforeChild);
  }
  appendInitialChild(child) {
    manualChildren.appendInitialChild.call(this, child);
  }
  appendChild(child) {
    manualChildren.appendChild.call(this, child);
  }
  close() {
    super.close();
  }
  setStyle(style, type = STYLE_TYPE.PART_MAIN) {
    setStyle({
      comp: this,
      styleSheet: style,
      compName: "Tabs",
      styleType: type,
      oldStyleSheet: null,
      isInit: false,
    });
  }
  moveToFront() {
    super.moveToFront();
  }
  moveToBackground() {
    super.moveToBackground();
  }
  scrollIntoView() {
    super.scrollIntoView();
  }
}
