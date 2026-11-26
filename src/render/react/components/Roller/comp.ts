// Generated from scripts/data/widgets_manifest.json. Do not edit by hand.
// Regenerate with: python3 autogen/ts_emitter.py
import { StyleProps } from "../../core/style";
import { CommonComponentApi, CommonProps, OnChangeEvent } from "../common/index";
import {
  EVENTTYPE_MAP,
  STYLE_TYPE,
  handleEvent,
  setStyle,
  styleGetterProp,
  applyDataPropsToDataset,
} from "../config";

import { GetBridge } from "../../core/bridge";

const bridge = GetBridge();
const NativeComp = bridge.NativeRender.NativeComponents.Roller;

export type RollerProps = CommonProps & {
  selectedStyle?: StyleProps;
  options: string[];
  selectIndex: number;
  visibleRowCount: number;
  onChange?: (event: OnChangeEvent) => void;
  /** Makes the roller circular */
  infinity?: boolean;
};

function setRollerProps(comp, newProps: RollerProps, oldProps: Partial<RollerProps>) {
  const setter = {
    ...CommonComponentApi({ compName: "Roller", comp, newProps, oldProps }),
    selectedStyle(styleSheet) {
      setStyle({
        comp,
        styleSheet,
        compName: "Roller",
        styleType: STYLE_TYPE.PART_SELECTED,
        oldStyleSheet: oldProps.selectedStyle,
      });
    },
    options(arr) {
      if (arr !== oldProps.options && Array.isArray(arr)) {
        comp.setOptions(arr, arr.length, !!newProps.infinity);
      }
    },
    selectIndex(val) {
      if (val !== oldProps.selectIndex) {
        comp.setSelectIndex(val);
      }
    },
    visibleRowCount(val) {
      if (val !== oldProps.visibleRowCount) {
        comp.setVisibleRowCount(val);
      }
    },
    onChange(fn) {
      handleEvent(comp, fn, EVENTTYPE_MAP.EVENT_VALUE_CHANGED);
    },
  };
  Object.keys(setter).forEach((key) => {
    if (newProps.hasOwnProperty(key)) {
      setter[key](newProps[key]);
    }
  });
  applyDataPropsToDataset(comp, newProps);
}

export class RollerComp extends NativeComp {
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
  setProps(newProps: RollerProps, oldProps: Partial<RollerProps>) {
    setRollerProps(this, newProps, oldProps);
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
      compName: "Roller",
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
