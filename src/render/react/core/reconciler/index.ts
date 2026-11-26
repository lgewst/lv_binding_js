import Reconciler from "react-reconciler";

import { getComponentByTagName } from "../../components/config";
import { LvgljsNativeComponent } from "../bridge";
import { unRegistEvent } from "../event";

let id = 1;

export const getUid = (): string => {
  return String(id++);
};

const HOST_CHILDREN = Symbol("hostChildren");
const DETACHED = Symbol("detached");

/**
 * What a component's createInstance returns: a native component plus the child
 * hooks the comp classes define, and the two marks this module keeps on it.
 */
export interface HostInstance extends LvgljsNativeComponent {
  appendChild?(child: HostInstance): void;
  appendInitialChild?(child: HostInstance): void;
  insertBefore?(child: HostInstance, beforeChild?: HostInstance): void;
  setText?(text: string): void;
  [HOST_CHILDREN]?: Set<HostInstance>;
  [DETACHED]?: boolean;
}

/** createContainer is handed a Set; appendChildToContainer adds to it. */
export type HostContainer = Set<HostInstance>;

// React reconciler 0.25.1 may skip per-child removeChild when an entire subtree is
// deleted (e.g. Mask + Calendar). Track host children ourselves so detachInstance can
// walk and close them before the parent.

const instanceMap = new Map<LvgljsNativeComponent["uid"], HostInstance>();

export const getInstance = (uid: LvgljsNativeComponent["uid"]): HostInstance | undefined => {
  return instanceMap.get(uid);
};

function trackHostChild(parent: HostInstance | null, child: HostInstance | null): void {
  if (!parent || !child) return;
  if (!parent[HOST_CHILDREN]) {
    parent[HOST_CHILDREN] = new Set();
  }
  parent[HOST_CHILDREN].add(child);
}

function untrackHostChild(parent: HostInstance | null, child: HostInstance): void {
  parent?.[HOST_CHILDREN]?.delete(child);
}

function mountHostChild(parent: HostInstance, child: HostInstance, attach: () => void): void {
  trackHostChild(parent, child);
  attach();
}

function detachInstance(instance: HostInstance | null): void {
  if (!instance?.uid || instance[DETACHED]) return;
  instance[DETACHED] = true;

  const children = instance[HOST_CHILDREN];
  if (children) {
    // Close children before this instance. LVGL deletes all child lv_objs when a
    // parent is lv_obj_delete'd; child close() must run first while the parent still
    // exists. Native removeChild does not reparent to the window root for this.
    for (const child of [...children]) {
      detachInstance(child);
    }
    instance[HOST_CHILDREN] = undefined;
  }

  unRegistEvent(instance.uid);
  instanceMap.delete(instance.uid);
  instance.style = null;
  instance.close?.();
}

/**
 * What a component's config actually implements. LvgljsComponentConfig in
 * components/config.ts derives these from the published HostConfig with every
 * generic set to any, which lines the parameters up one position off: its
 * createInstance starts with the element type where ours starts with props, and
 * its commitUpdate takes six arguments where ours takes five. All-any hid that.
 * The real shapes are written out here so the calls below are checked; putting
 * them in components/config.ts is a change for that file's own commit.
 */
interface ComponentConfig {
  createInstance: (
    newProps: Record<string, unknown>,
    rootInstance: HostContainer,
    context: unknown,
    workInProgress: unknown,
    uid: string,
  ) => HostInstance;
  commitMount: (
    instance: HostInstance,
    newProps: Record<string, unknown>,
    internalInstanceHandle: unknown,
  ) => void;
  commitUpdate: (
    instance: HostInstance,
    updatePayload: unknown,
    oldProps: Record<string, unknown>,
    newProps: Record<string, unknown>,
    finishedWork: unknown,
  ) => void;
}

function configFor(type: string): ComponentConfig {
  return getComponentByTagName(type) as unknown as ComponentConfig;
}

/**
 * The installed react-reconciler is 0.25.1 while @types/react-reconciler is 0.18,
 * so the published HostConfig does not describe every member this version calls
 * (detachDeletedInstance among them). The fields are typed here and the whole
 * object is handed to Reconciler through one cast at that boundary.
 */
interface LvgljsHostConfig {
  now: () => number;
  supportsMutation: boolean;
  getPublicInstance: (instance: HostInstance) => HostInstance;
  getRootHostContext: () => { name: string };
  prepareForCommit: () => void;
  resetAfterCommit: () => void;
  getChildHostContext: () => Record<string, never>;
  shouldSetTextContent: (type: string, props: Record<string, unknown>) => boolean;
  createInstance: (
    type: string,
    newProps: Record<string, unknown>,
    rootContainerInstance: HostContainer,
    currentHostContext: unknown,
    workInProgress: unknown,
  ) => HostInstance;
  createTextInstance: (
    text: string,
    rootContainerInstance: HostContainer,
    context: unknown,
    workInProgress: unknown,
  ) => null;
  appendInitialChild: (parent: HostInstance, child: HostInstance) => void;
  appendChild: (parent: HostInstance, child: HostInstance) => void;
  finalizeInitialChildren: (
    instance: HostInstance,
    type: string,
    props: Record<string, unknown>,
  ) => boolean;
  insertBefore: (
    parent: HostInstance,
    child: HostInstance,
    beforeChild: HostInstance,
  ) => void;
  appendChildToContainer: (container: HostContainer, child: HostInstance) => void;
  insertInContainerBefore: (
    container: HostContainer,
    child: HostInstance,
    beforeChild: HostInstance,
  ) => void;
  removeChildFromContainer: (container: HostContainer, child: HostInstance) => void;
  prepareUpdate: (
    instance: HostInstance,
    oldProps: Record<string, unknown>,
    newProps: Record<string, unknown>,
  ) => boolean;
  commitUpdate: (
    instance: HostInstance,
    updatePayload: unknown,
    type: string,
    oldProps: Record<string, unknown>,
    newProps: Record<string, unknown>,
    finishedWork: unknown,
  ) => void;
  commitTextUpdate: (
    textInstance: HostInstance,
    oldText: string,
    newText: string,
  ) => void;
  detachDeletedInstance: (instance: HostInstance) => void;
  removeChild: (parent: HostInstance, child: HostInstance) => void;
  commitMount: (
    instance: HostInstance,
    type: string,
    newProps: Record<string, unknown>,
    internalInstanceHandle: unknown,
  ) => void;
}

const HostConfig: LvgljsHostConfig = {
  now: Date.now,
  getPublicInstance: (instance) => {
    //for supporting refs
    return instance;
  },
  getRootHostContext: () => {
    let context = {
      name: "rootnode",
    };
    return context;
  },
  prepareForCommit: () => {},
  resetAfterCommit: () => {},
  getChildHostContext: () => {
    return {};
  },
  shouldSetTextContent: function (type, props) {
    return false;
  },
  createInstance: (
    type,
    newProps,
    rootContainerInstance,
    _currentHostContext,
    workInProgress,
  ) => {
    const { createInstance } = configFor(type);
    const uid = getUid();
    const instance = createInstance(
      newProps,
      rootContainerInstance,
      _currentHostContext,
      workInProgress,
      uid,
    );
    return instance;
  },
  createTextInstance: (
    text,
    rootContainerInstance,
    context,
    workInProgress,
  ) => {
    return null;
  },
  appendInitialChild: (parent, child) => {
    mountHostChild(parent, child, () => parent.appendChild?.(child));
  },
  appendChild(parent, child) {
    mountHostChild(parent, child, () => parent.appendChild?.(child));
  },
  finalizeInitialChildren: (yueElement, type, props) => {
    return true;
  },
  insertBefore: (parent, child, beforeChild) => {
    mountHostChild(parent, child, () => parent.insertBefore?.(child, beforeChild));
  },
  supportsMutation: true,
  appendChildToContainer: function (container, child) {
    container.add(child);
  },
  insertInContainerBefore: (container, child, beforeChild) => {
    container.add(child);
  },
  removeChildFromContainer: (container, child) => {
    container.delete(child);
    detachInstance(child);
  },
  prepareUpdate(instance, oldProps, newProps) {
    return true;
  },
  commitUpdate: function (
    instance,
    updatePayload,
    type,
    oldProps,
    newProps,
    finishedWork,
  ) {
    const { commitUpdate } = configFor(type);
    return commitUpdate(
      instance,
      updatePayload,
      oldProps,
      newProps,
      finishedWork,
    );
  },
  commitTextUpdate(textInstance, oldText, newText) {
    textInstance.setText?.(newText);
  },
  detachDeletedInstance: (instance) => {
    detachInstance(instance);
  },
  removeChild(parent, child) {
    // Host child removal is JS-only: untrack, then detachInstance (close()).
    // No native removeChild; lv_obj teardown runs in BasicComponent destructor.
    untrackHostChild(parent, child);
    detachInstance(child);
  },
  commitMount: function (instance, type, newProps, internalInstanceHandle) {
    instanceMap.set(instance.uid, instance);
    const { commitMount } = configFor(type);
    return commitMount(instance, newProps, internalInstanceHandle);
  },
};

/**
 * The three members this project uses, with 0.25.1's own signatures.
 * react-reconciler 0.25.1's createContainer takes (containerInfo, tag, hydrate,
 * hydrationCallbacks) and both trailing arguments are optional in practice;
 * @types 0.18 declares a different arity, so the surface is written out here
 * rather than taken from the published types.
 */
export interface LvgljsReconciler {
  createContainer(
    containerInfo: HostContainer,
    tag?: unknown,
    hydrate?: boolean,
    hydrationCallbacks?: unknown,
  ): OpaqueRoot;
  updateContainer(
    element: unknown,
    container: OpaqueRoot,
    parentComponent?: unknown,
    callback?: () => void,
  ): void;
  injectIntoDevTools(config: unknown): void;
}

/** createFiberRoot's return value; this project only ever passes it back. */
export type OpaqueRoot = { readonly __fiberRoot: unique symbol };

export default Reconciler(HostConfig as never) as unknown as LvgljsReconciler;
