// Generated from scripts/data/widgets_manifest.json. Do not edit by hand.
// Regenerate with: python3 autogen/ts_emitter.py
import { LvgljsComponentConfig } from "../config";
import { MaskComp, MaskProps } from "./comp";

export default class MaskConfig implements LvgljsComponentConfig<MaskProps, MaskComp> {
  tagName = "Mask";
  shouldSetTextContent() {
    return false;
  }
  createInstance(newProps: MaskProps, rootInstance, context, workInProgress, uid) {
    const instance = new MaskComp({ uid });
    instance.setProps(newProps, {});
    return instance;
  }
  commitMount(instance, newProps: MaskProps, internalInstanceHandle) {}
  commitUpdate(instance, updatePayload, oldProps: MaskProps, newProps: MaskProps, finishedWork) {
    instance.setProps(newProps, oldProps);
  }
  commitUnmount(instance) {}
  setProps(newProps: MaskProps, oldProps: MaskProps) {}
  insertBefore(child, beforeChild) {}
  appendInitialChild(child) {}
  appendChild(child) {}
}
