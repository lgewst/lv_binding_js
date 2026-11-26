import type { LvgljsEvent } from "./core/event";

declare global {
  /**
   * Set by core/event. The native side looks this up on globalThis and calls it
   * to deliver an event; see FIRE_QEVENT_CALLBACK in src/render/native.
   */
  var FIRE_QEVENT_CALLBACK: (
    targetUid: string | number,
    currentTargetUid: string | number,
    eventType: number,
    event: LvgljsEvent,
  ) => void;

  /** Set by core/animate; animate.cpp calls it with the callback uid then the value. */
  var ANIMIATE_CALLBACK: (cbUid: number, ...args: number[]) => void;

  /** Object branch of {@link StylePropValueCSS}; interface breaks alias self-reference. */
  export interface StylePropValueCSSMap {
    readonly [key: string]: StylePropValueCSS;
  }

  export type StylePropValueCSS =
    | null
    | string
    | number
    | boolean
    | readonly StylePropValueCSS[]
    | StylePropValueCSSMap;

  export type StylePropValue =
    | undefined
    | null
    | number
    | string
    | boolean
    | readonly StylePropValueCSS[]
    | StylePropValueCSSMap;

  /** Packed prop id + StylePropValueKind in bits 30-31; parallel to batch.values[i]. */
  export type NativeStyleBatch = {
    readonly keys: Uint32Array;
    readonly values: StylePropValue[];
  };

  /** [count, props[], durationMs, timingFunctionIndex, delayMs] read by C++ setTransition. */
  export type NativeStylePropTransition = readonly [
    number,
    readonly number[],
    number,
    number,
    number,
  ];

  export type NativeStylePayload = {
    batch: NativeStyleBatch;
    transition?: NativeStylePropTransition;
  };

}

export {};
