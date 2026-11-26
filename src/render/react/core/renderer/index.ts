import reconciler, { HostContainer, OpaqueRoot } from "../reconciler";

const containerInfo: HostContainer = new Set();

export class Renderer {
  static container: OpaqueRoot;
  static portalContainer: OpaqueRoot;

  static render(element: unknown, options?: unknown) {
    const isConcurrent = true;
    const hydrate = false;

    Renderer.container = reconciler.createContainer(
      containerInfo,
      isConcurrent,
      hydrate,
    );

    const parentComponent = null;
    reconciler.updateContainer(element, Renderer.container, parentComponent);
  }
}
