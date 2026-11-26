import { LvgljsNativeComponent } from "../bridge";
import { getInstance } from "../reconciler";
import { EVENT_TYPE_MAP } from "../lv_types";

/** Instance uid, as LvgljsNativeComponent carries it. */
type Uid = string | number;

/** One of EVENT_TYPE_MAP's values; C++ reads it with JS_ToInt32. */
type EventType = number;

/**
 * What a handler receives. The native side builds the payload and this module
 * fills in target and currentTarget before the call.
 */
export interface LvgljsEvent {
  target?: LvgljsNativeComponent;
  currentTarget?: LvgljsNativeComponent;
  [key: string]: unknown;
}

export type EventHandler = (event: LvgljsEvent) => void;

const eventMap: Record<Uid, Record<EventType, EventHandler>> = {};

/** @deprecated Use EVENT_TYPE_MAP from lv_types; kept for existing imports. */
export const EVENTTYPE_MAP = EVENT_TYPE_MAP;

export function registEvent(uid: Uid, eventType: EventType, fn: EventHandler): void {
  eventMap[uid] = eventMap[uid] || {};
  eventMap[uid][eventType] = fn;
}

export function unRegistEvent(uid: Uid, eventType?: EventType): void {
  if (!eventType) {
    delete eventMap[uid];
  } else {
    const obj = eventMap[uid];
    obj && delete obj[eventType];
  }
}

export function fireEvent(
  targetUid: Uid,
  currentTargetUid: Uid,
  eventType: EventType,
  e: LvgljsEvent,
): void {
  const obj = eventMap[currentTargetUid];
  const target = getInstance(targetUid);
  const currentTarget = getInstance(currentTargetUid);
  if (obj) {
    e.target = target;
    e.currentTarget = currentTarget;
    try {
      obj[eventType].call(null, e);
    } catch (err) {
      console.log(err);
    }
  }
}

export function handleEvent(
  comp: LvgljsNativeComponent,
  fn: EventHandler | undefined,
  type: EventType,
): void {
  if (fn) {
    registEvent(comp.uid, type, fn);
    comp.addEventListener(type);
  } else {
    unRegistEvent(comp.uid, type);
    comp.removeEventListener(type);
  }
}

// The native side calls this to deliver an event; see qevent in src/render/native.
globalThis.FIRE_QEVENT_CALLBACK = fireEvent;
