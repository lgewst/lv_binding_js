// Generated from scripts/data/widgets_manifest.json. Do not edit by hand.
// Regenerate with: python3 autogen/ts_emitter.py
import { StyleProps } from "../../core/style";
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
const NativeComp = bridge.NativeRender.NativeComponents.ProgressBar;

export type ProgressBarProps = CommonProps & {
  indicatorStyle?: StyleProps;
  value: number;
  range: number[];
  style?: StyleProps;
  animationTime?: number;
  useAnimation?: boolean;
};

function setProgressBarProps(comp, newProps: ProgressBarProps, oldProps: Partial<ProgressBarProps>) {
  const manual = manualSetters({ comp, newProps, oldProps });
  const setter = {
    ...CommonComponentApi({ compName: "ProgressBar", comp, newProps, oldProps }),
    style: manual.style,
    indicatorStyle(styleSheet) {
      setStyle({
        comp,
        styleSheet,
        compName: "ProgressBar",
        styleType: STYLE_TYPE.PART_INDICATOR,
        oldStyleSheet: oldProps.style,
      });
    },
    value(val) {
      if (val !== oldProps.value) {
        comp.setValue(val, !!newProps.useAnimation);
      }
    },
    range(arr) {
      if (!Array.isArray(arr)) return;
      if (arr[0] === oldProps.range?.[0] && arr[1] === oldProps.range?.[1]) return;
      comp.setRange(arr[0], arr[1]);
    },
  };
  Object.keys(setter).forEach((key) => {
    if (newProps.hasOwnProperty(key)) {
      setter[key](newProps[key]);
    }
  });
  applyDataPropsToDataset(comp, newProps);
}

export class ProgressBarComp extends NativeComp {
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
  setProps(newProps: ProgressBarProps, oldProps: Partial<ProgressBarProps>) {
    setProgressBarProps(this, newProps, oldProps);
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
      compName: "ProgressBar",
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
