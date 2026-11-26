// Generated from scripts/data/widgets_manifest.json. Do not edit by hand.
// Regenerate with: python3 autogen/ts_emitter.py
import * as lv_conf from "../../core/lv_conf";
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
import { InputComp } from "../Input/comp";
import { manualSetters } from "./manual";

const bridge = GetBridge();
const NativeComp = bridge.NativeRender.NativeComponents.Keyboard;

const modes = {
  lower: lv_conf.LV_KEYBOARD_MODE_TEXT_LOWER,
  upper: lv_conf.LV_KEYBOARD_MODE_TEXT_UPPER,
  special: lv_conf.LV_KEYBOARD_MODE_SPECIAL,
  number: lv_conf.LV_KEYBOARD_MODE_NUMBER,
};

export type KeyboardProps = CommonProps & {
  mode: "lower" | "upper" | "special" | "number";
  onClose?: () => void;
  onOk?: () => void;
  textarea: InputComp;
};

function setKeyboardProps(comp, newProps: KeyboardProps, oldProps: Partial<KeyboardProps>) {
  const manual = manualSetters({ comp, newProps, oldProps });
  const setter = {
    ...CommonComponentApi({ compName: "Keyboard", comp, newProps, oldProps }),
    mode(val) {
      if (val !== oldProps.mode && typeof modes[val] !== "undefined") {
        comp.setMode(modes[val]);
      }
    },
    textarea: manual.textarea,
    onClose(fn) {
      handleEvent(comp, fn, EVENTTYPE_MAP.EVENT_CANCEL);
    },
    onOk(fn) {
      handleEvent(comp, fn, EVENTTYPE_MAP.EVENT_READY);
    },
  };
  Object.keys(setter).forEach((key) => {
    if (newProps.hasOwnProperty(key)) {
      setter[key](newProps[key]);
    }
  });
  applyDataPropsToDataset(comp, newProps);
}

export class KeyboardComp extends NativeComp {
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
  setProps(newProps: KeyboardProps, oldProps: Partial<KeyboardProps>) {
    setKeyboardProps(this, newProps, oldProps);
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
      compName: "Keyboard",
      styleType: type,
      oldStyleSheet: {},
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
