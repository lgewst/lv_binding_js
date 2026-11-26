// Generated from scripts/data/widgets_manifest.json. Do not edit by hand.
// Regenerate with: python3 autogen/ts_emitter.py
import { LvgljsComponentConfig } from "../config";
import { ImageComp, ImageProps } from "./comp";

export default class ImageConfig implements LvgljsComponentConfig<ImageProps, ImageComp> {
  tagName = "Image";
  shouldSetTextContent() {
    return false;
  }
  createInstance(newProps: ImageProps, rootInstance, context, workInProgress, uid) {
    const instance = new ImageComp({ uid });
    instance.setProps(newProps, {});
    return instance;
  }
  commitMount(instance, newProps: ImageProps, internalInstanceHandle) {}
  commitUpdate(instance, updatePayload, oldProps: ImageProps, newProps: ImageProps, finishedWork) {
    instance.setProps(newProps, oldProps);
  }
  commitUnmount(instance) {}
  setProps(newProps: ImageProps, oldProps: ImageProps) {}
  insertBefore(child, beforeChild) {}
  appendInitialChild(child) {}
  appendChild(child) {}
}
