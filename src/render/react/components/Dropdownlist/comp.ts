// Generated from scripts/data/widgets_manifest.json. Do not edit by hand.
// Regenerate with: python3 autogen/ts_emitter.py
import { CommonComponentApi, CommonProps, OnChangeEvent } from "../common/index";
import {
  EDropdownListArrowDirection,
  EDropdownlistDirection,
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
const NativeComp = bridge.NativeRender.NativeComponents.Dropdownlist;

export type DropdownListProps = CommonProps & {
  items: string[];
  selectIndex: number;
  /** If the text is null the selected option is displayed on the items */
  text?: string;
  direction: typeof EDropdownlistDirection[keyof typeof EDropdownlistDirection];
  highlightSelect: boolean;
  onChange?: (event: OnChangeEvent) => void;
  arrow: typeof EDropdownListArrowDirection[keyof typeof EDropdownListArrowDirection];
};

function setDropdownListProps(comp, newProps: DropdownListProps, oldProps: Partial<DropdownListProps>) {
  const manual = manualSetters({ comp, newProps, oldProps });
  const setter = {
    ...CommonComponentApi({ compName: "Dropdownlist", comp, newProps, oldProps }),
    items(arr) {
      if (arr !== oldProps.items && Array.isArray(arr)) {
        comp.setItems(arr, arr.length);
      }
    },
    arrow: manual.arrow,
    selectIndex(val) {
      if (val !== oldProps.selectIndex) {
        comp.setSelectIndex(val);
      }
    },
    text(val) {
      if (val !== oldProps.text) {
        comp.setText(val);
      }
    },
    direction(val) {
      if (val !== oldProps.direction) {
        comp.setDir(val);
      }
    },
    highlightSelect(val) {
      if (val != oldProps.highlightSelect) {
        comp.setHighLightSelect(val);
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

export class DropdownlistComp extends NativeComp {
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
  setProps(newProps: DropdownListProps, oldProps: Partial<DropdownListProps>) {
    setDropdownListProps(this, newProps, oldProps);
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
      compName: "Dropdownlist",
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
