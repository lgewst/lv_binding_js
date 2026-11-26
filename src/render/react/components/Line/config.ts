// Generated from scripts/data/widgets_manifest.json. Do not edit by hand.
// Regenerate with: python3 autogen/ts_emitter.py
import { LvgljsComponentConfig } from "../config";
import { LineComp, LineProps } from "./comp";

export default class LineConfig implements LvgljsComponentConfig<LineProps, LineComp> {
  tagName = "Line";
  shouldSetTextContent() {
    return false;
  }
  createInstance(newProps: LineProps, rootInstance, context, workInProgress, uid) {
    const instance = new LineComp({ uid });
    instance.setProps(newProps, {});
    return instance;
  }
  commitMount(instance, newProps: LineProps, internalInstanceHandle) {}
  commitUpdate(instance, updatePayload, oldProps: LineProps, newProps: LineProps, finishedWork) {
    instance.setProps(newProps, oldProps);
  }
  commitUnmount(instance) {}
  setProps(newProps: LineProps, oldProps: LineProps) {}
  insertBefore(child, beforeChild) {}
  appendInitialChild(child) {}
  appendChild(child) {}
}
