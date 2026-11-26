// Generated from scripts/data/widgets_manifest.json. Do not edit by hand.
// Regenerate with: python3 autogen/ts_emitter.py
import { StyleProps } from "../../core/style";
import { CommonComponentApi, CommonProps, OnChangeEvent, OnClickEvent } from "../common/index";
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
const NativeComp = bridge.NativeRender.NativeComponents.Textarea;

export type InputProps = CommonProps & {
  placeholder: string;
  /** Maximum number of characters */
  maxlength: number;
  onChange?: (event: OnChangeEvent) => void;
  onFocus?: (event: OnClickEvent) => void;
  onBlur?: (event: OnClickEvent) => void;
  onFocusStyle: StyleProps;
  value: string;
  /** Virtual keyboard will auto raise up when focus on Input component */
  autoKeyBoard: boolean;
  /** `password` mode changes text to `*` */
  mode?: "password" | "text";
};

function setInputProps(comp, newProps: InputProps, oldProps: Partial<InputProps>) {
  const manual = manualSetters({ comp, newProps, oldProps });
  const setter = {
    ...CommonComponentApi({ compName: "Input", comp, newProps, oldProps }),
    placeholder(val) {
      if (val !== oldProps.placeholder) {
        comp.setPlaceHolder(val);
      }
    },
    mode: manual.mode,
    maxlength(val) {
      if (val !== oldProps.maxlength) {
        comp.setMaxLength(val);
      }
    },
    onChange(fn) {
      handleEvent(comp, fn, EVENTTYPE_MAP.EVENT_VALUE_CHANGED);
    },
    onFocus(fn) {
      handleEvent(comp, fn, EVENTTYPE_MAP.EVENT_FOCUSED);
    },
    onBlur(fn) {
      handleEvent(comp, fn, EVENTTYPE_MAP.EVENT_DEFOCUSED);
    },
    onFocusStyle(styleSheet) {
      setStyle({
        comp,
        styleSheet,
        compName: "Input",
        styleType: STYLE_TYPE.STATE_FOCUSED,
        oldStyleSheet: oldProps.onFocusStyle,
      });
    },
    value(val) {
      if (val !== oldProps.value) {
        comp.setText(val);
      }
    },
    autoKeyBoard(val) {
      if (val !== oldProps.autoKeyBoard) {
        comp.setAutoKeyboard(val);
      }
    },
  };
  Object.keys(setter).forEach((key) => {
    if (newProps.hasOwnProperty(key)) {
      setter[key](newProps[key]);
    }
  });
  applyDataPropsToDataset(comp, newProps);
}

export class InputComp extends NativeComp {
  constructor({ uid }) {
    super({ uid });
    this.uid = uid;
    super.setOneLine(true);

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
  setProps(newProps: InputProps, oldProps: Partial<InputProps>) {
    setInputProps(this, newProps, oldProps);
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
      compName: "Input",
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
