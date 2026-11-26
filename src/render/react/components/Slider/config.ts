// Generated from scripts/data/widgets_manifest.json. Do not edit by hand.
// Regenerate with: python3 autogen/ts_emitter.py
import { LvgljsComponentConfig } from "../config";
import { SliderComp, SliderProps } from "./comp";

export default class SliderConfig implements LvgljsComponentConfig<SliderProps, SliderComp> {
  tagName = "Slider";
  shouldSetTextContent() {
    return false;
  }
  createInstance(newProps: SliderProps, rootInstance, context, workInProgress, uid) {
    const instance = new SliderComp({ uid });
    instance.setProps(newProps, {});
    return instance;
  }
  commitMount(instance, newProps: SliderProps, internalInstanceHandle) {}
  commitUpdate(instance, updatePayload, oldProps: SliderProps, newProps: SliderProps, finishedWork) {
    instance.setProps(newProps, oldProps);
  }
  commitUnmount(instance) {}
  setProps(newProps: SliderProps, oldProps: SliderProps) {}
  insertBefore(child, beforeChild) {}
  appendInitialChild(child) {}
  appendChild(child) {}
}
