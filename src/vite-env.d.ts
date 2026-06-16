/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_LSL_ENABLED?: string;
  readonly VITE_LSL_WS_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
