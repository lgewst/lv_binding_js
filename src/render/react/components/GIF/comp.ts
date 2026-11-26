// Generated from scripts/data/widgets_manifest.json. Do not edit by hand.
// Regenerate with: python3 autogen/ts_emitter.py
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
import { manualSetters } from "./manual";

const bridge = GetBridge();
const NativeComp = bridge.NativeRender.NativeComponents.GIF;

export type GIFProps = CommonProps & {
  src: string;
  paused?: boolean;
};

function setGIFProps(comp, newProps: GIFProps, oldProps: Partial<GIFProps>) {
  const manual = manualSetters({ comp, newProps, oldProps });
  const setter = {
    ...CommonComponentApi({ compName: "GIF", comp, newProps, oldProps }),
    src: manual.src,
    paused: manual.paused,
  };
  Object.keys(setter).forEach((key) => {
    if (newProps.hasOwnProperty(key)) {
      setter[key](newProps[key]);
    }
  });
  applyDataPropsToDataset(comp, newProps);
}

export class GIFComp extends NativeComp {
  constructor({ uid }) {
    super({ uid });
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
  }
  setProps(newProps: GIFProps, oldProps: Partial<GIFProps>) {
    setGIFProps(this, newProps, oldProps);
  }
  insertBefore(child, beforeChild) {}
  appendInitialChild(child) {}
  appendChild(child) {}
  close() {
    super.close();
  }
  setStyle(style, type = STYLE_TYPE.PART_MAIN) {
    setStyle({
      comp: this,
      styleSheet: style,
      compName: "GIF",
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
