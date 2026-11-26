// Generated from scripts/data/widgets_manifest.json. Do not edit by hand.
// Regenerate with: python3 autogen/ts_emitter.py
import { LvgljsComponentConfig } from "../config";
import { ArcComp, ArcProps } from "./comp";

export default class ArcConfig implements LvgljsComponentConfig<ArcProps, ArcComp> {
  tagName = "Arc";
  shouldSetTextContent() {
    return false;
  }
  createInstance(newProps: ArcProps, rootInstance, context, workInProgress, uid) {
    const instance = new ArcComp({ uid });
    instance.setProps(newProps, {});
    return instance;
  }
  commitMount(instance, newProps: ArcProps, internalInstanceHandle) {}
  commitUpdate(instance, updatePayload, oldProps: ArcProps, newProps: ArcProps, finishedWork) {
    instance.setProps(newProps, oldProps);
  }
  commitUnmount(instance) {}
  setProps(newProps: ArcProps, oldProps: ArcProps) {}
  insertBefore(child, beforeChild) {}
  appendInitialChild(child) {}
  appendChild(child) {}
}
