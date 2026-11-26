// Generated from scripts/data/widgets_manifest.json. Do not edit by hand.
// Regenerate with: python3 autogen/ts_emitter.py
import { LvgljsComponentConfig } from "../config";
import { CalendarComp, CalendarProps } from "./comp";

export default class CalendarConfig implements LvgljsComponentConfig<CalendarProps, CalendarComp> {
  tagName = "Calendar";
  shouldSetTextContent() {
    return false;
  }
  createInstance(newProps: CalendarProps, rootInstance, context, workInProgress, uid) {
    const instance = new CalendarComp({ uid });
    instance.setProps(newProps, {});
    return instance;
  }
  commitMount(instance, newProps: CalendarProps, internalInstanceHandle) {}
  commitUpdate(instance, updatePayload, oldProps: CalendarProps, newProps: CalendarProps, finishedWork) {
    instance.setProps(newProps, oldProps);
  }
  commitUnmount(instance) {}
  setProps(newProps: CalendarProps, oldProps: CalendarProps) {}
  insertBefore(child, beforeChild) {}
  appendInitialChild(child) {}
  appendChild(child) {}
}
