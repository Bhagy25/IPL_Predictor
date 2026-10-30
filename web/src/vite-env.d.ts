/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Absolute API base for a split deployment; unset means the same-origin "/api". */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
