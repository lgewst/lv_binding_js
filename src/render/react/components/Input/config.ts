// Generated from scripts/data/widgets_manifest.json. Do not edit by hand.
// Regenerate with: python3 autogen/ts_emitter.py
import { LvgljsComponentConfig } from "../config";
import { InputComp, InputProps } from "./comp";

export default class InputConfig implements LvgljsComponentConfig<InputProps, InputComp> {
  tagName = "Input";
  shouldSetTextContent() {
    return false;
  }
  createInstance(newProps: InputProps, rootInstance, context, workInProgress, uid) {
    const instance = new InputComp({ uid });
    instance.setProps(newProps, {});
    return instance;
  }
  commitMount(instance, newProps: InputProps, internalInstanceHandle) {}
  commitUpdate(instance, updatePayload, oldProps: InputProps, newProps: InputProps, finishedWork) {
    instance.setProps(newProps, oldProps);
  }
  commitUnmount(instance) {}
  setProps(newProps: InputProps, oldProps: InputProps) {}
  insertBefore(child, beforeChild) {}
  appendInitialChild(child) {}
  appendChild(child) {}
}
