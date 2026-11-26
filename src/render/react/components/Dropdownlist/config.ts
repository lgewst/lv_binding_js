// Generated from scripts/data/widgets_manifest.json. Do not edit by hand.
// Regenerate with: python3 autogen/ts_emitter.py
import { LvgljsComponentConfig } from "../config";
import { DropdownlistComp, DropdownListProps } from "./comp";

export default class DropdownlistConfig implements LvgljsComponentConfig<DropdownListProps, DropdownlistComp> {
  tagName = "Dropdownlist";
  shouldSetTextContent() {
    return false;
  }
  createInstance(newProps: DropdownListProps, rootInstance, context, workInProgress, uid) {
    const instance = new DropdownlistComp({ uid });
    instance.setProps(newProps, {});
    return instance;
  }
  commitMount(instance, newProps: DropdownListProps, internalInstanceHandle) {}
  commitUpdate(instance, updatePayload, oldProps: DropdownListProps, newProps: DropdownListProps, finishedWork) {
    instance.setProps(newProps, oldProps);
  }
  commitUnmount(instance) {}
  setProps(newProps: DropdownListProps, oldProps: DropdownListProps) {}
  insertBefore(child, beforeChild) {}
  appendInitialChild(child) {}
  appendChild(child) {}
}
