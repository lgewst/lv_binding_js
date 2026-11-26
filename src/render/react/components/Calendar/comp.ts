// Generated from scripts/data/widgets_manifest.json. Do not edit by hand.
// Regenerate with: python3 autogen/ts_emitter.py
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
import { manualSetters } from "./manual";

const bridge = GetBridge();
const NativeComp = bridge.NativeRender.NativeComponents.Calendar;

export type CalendarProps = CommonProps & {
  onChange?: (event: OnChangeEvent) => void;
  today?: string;
  shownMonth?: string;
  highLightDates?: string[];
};

function setCalendarProps(comp, newProps: CalendarProps, oldProps: Partial<CalendarProps>) {
  const manual = manualSetters({ comp, newProps, oldProps });
  const setter = {
    ...CommonComponentApi({ compName: "Calendar", comp, newProps, oldProps }),
    onChange(fn) {
      handleEvent(comp, fn, EVENTTYPE_MAP.EVENT_VALUE_CHANGED);
    },
    today: manual.today,
    shownMonth: manual.shownMonth,
    highLightDates: manual.highLightDates,
  };
  Object.keys(setter).forEach((key) => {
    if (newProps.hasOwnProperty(key)) {
      setter[key](newProps[key]);
    }
  });
  applyDataPropsToDataset(comp, newProps);
}

export class CalendarComp extends NativeComp {
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
  setProps(newProps: CalendarProps, oldProps: Partial<CalendarProps>) {
    setCalendarProps(this, newProps, oldProps);
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
      compName: "Calendar",
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
