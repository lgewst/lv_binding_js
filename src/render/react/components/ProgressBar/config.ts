// Generated from scripts/data/widgets_manifest.json. Do not edit by hand.
// Regenerate with: python3 autogen/ts_emitter.py
import { LvgljsComponentConfig } from "../config";
import { ProgressBarComp, ProgressBarProps } from "./comp";

export default class ProgressBarConfig implements LvgljsComponentConfig<ProgressBarProps, ProgressBarComp> {
  tagName = "ProgressBar";
  shouldSetTextContent() {
    return false;
  }
  createInstance(newProps: ProgressBarProps, rootInstance, context, workInProgress, uid) {
    const instance = new ProgressBarComp({ uid });
    instance.setProps(newProps, {});
    return instance;
  }
  commitMount(instance, newProps: ProgressBarProps, internalInstanceHandle) {}
  commitUpdate(instance, updatePayload, oldProps: ProgressBarProps, newProps: ProgressBarProps, finishedWork) {
    instance.setProps(newProps, oldProps);
  }
  commitUnmount(instance) {}
  setProps(newProps: ProgressBarProps, oldProps: ProgressBarProps) {}
  insertBefore(child, beforeChild) {}
  appendInitialChild(child) {}
  appendChild(child) {}
}
