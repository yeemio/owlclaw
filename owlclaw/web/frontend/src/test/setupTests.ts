import "@testing-library/jest-dom";

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Recharts needs ResizeObserver in test runtime.
(globalThis as any).ResizeObserver = ResizeObserverMock;
