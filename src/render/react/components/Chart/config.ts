// Generated from scripts/data/widgets_manifest.json. Do not edit by hand.
// Regenerate with: python3 autogen/ts_emitter.py
import { LvgljsComponentConfig } from "../config";
import { ChartComp, ChartProps } from "./comp";

export default class ChartConfig implements LvgljsComponentConfig<ChartProps, ChartComp> {
  tagName = "Chart";
  shouldSetTextContent() {
    return false;
  }
  createInstance(newProps: ChartProps, rootInstance, context, workInProgress, uid) {
    const instance = new ChartComp({ uid });
    instance.setProps(newProps, {});
    return instance;
  }
  commitMount(instance, newProps: ChartProps, internalInstanceHandle) {}
  commitUpdate(instance, updatePayload, oldProps: ChartProps, newProps: ChartProps, finishedWork) {
    instance.setProps(newProps, oldProps);
  }
  commitUnmount(instance) {}
  setProps(newProps: ChartProps, oldProps: ChartProps) {}
  insertBefore(child, beforeChild) {}
  appendInitialChild(child) {}
  appendChild(child) {}
}
