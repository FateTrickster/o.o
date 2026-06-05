declare namespace NodeJS {
  interface ProcessEnv {
    LLM_PROVIDER?: "mock" | "openai" | "deepseek" | "xfyun" | string;
    AI_LITERACY_OPENAI_API_KEY?: string;
    OPENAI_API_KEY?: string;
    OPENAI_MODEL?: string;
    OPENAI_BASE_URL?: string;
    XFYUN_MAAS_API_KEY?: string;
    XFYUN_MAAS_MODEL?: string;
    XFYUN_MAAS_BASE_URL?: string;
    AI_LITERACY_DEEPSEEK_API_KEY?: string;
    DEEPSEEK_API_KEY?: string;
    DEEPSEEK_MODEL?: string;
    DEEPSEEK_BASE_URL?: string;
  }
}
