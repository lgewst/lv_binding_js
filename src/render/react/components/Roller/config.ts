// Generated from scripts/data/widgets_manifest.json. Do not edit by hand.
// Regenerate with: python3 autogen/ts_emitter.py
import { LvgljsComponentConfig } from "../config";
import { RollerComp, RollerProps } from "./comp";

export default class RollerConfig implements LvgljsComponentConfig<RollerProps, RollerComp> {
  tagName = "Roller";
  shouldSetTextContent() {
    return false;
  }
  createInstance(newProps: RollerProps, rootInstance, context, workInProgress, uid) {
    const instance = new RollerComp({ uid });
    instance.setProps(newProps, {});
    return instance;
  }
  commitMount(instance, newProps: RollerProps, internalInstanceHandle) {}
  commitUpdate(instance, updatePayload, oldProps: RollerProps, newProps: RollerProps, finishedWork) {
    instance.setProps(newProps, oldProps);
  }
  commitUnmount(instance) {}
  setProps(newProps: RollerProps, oldProps: RollerProps) {}
  insertBefore(child, beforeChild) {}
  appendInitialChild(child) {}
  appendChild(child) {}
}
