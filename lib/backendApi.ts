import { NextRequest, NextResponse } from "next/server";

const backendBaseUrl = (process.env.PYTHON_API_BASE_URL || "http://127.0.0.1:8000").replace(
  /\/$/,
  ""
);

function toBackendUrl(path: string, search = "") {
  return `${backendBaseUrl}${path}${search}`;
}

function backendError(payload: unknown, fallback: string) {
  if (payload && typeof payload === "object") {
    const record = payload as Record<string, unknown>;
    if (typeof record.error === "string") {
      return record.error;
    }
    if (typeof record.detail === "string") {
      return record.detail;
    }
    if (record.detail) {
      return JSON.stringify(record.detail);
    }
  }

  return fallback;
}

async function toJsonResponse(response: Response, fallbackMessage: string) {
  const text = await response.text();
  let payload: unknown = null;

  try {
    payload = text ? (JSON.parse(text) as unknown) : null;
  } catch {
    return NextResponse.json(
      { error: response.ok ? fallbackMessage : `${fallbackMessage}: backend returned non-JSON` },
      { status: response.ok ? 502 : response.status }
    );
  }

  if (!response.ok) {
    return NextResponse.json(
      { error: backendError(payload, fallbackMessage) },
      { status: response.status }
    );
  }

  return NextResponse.json(payload, { status: response.status });
}

export async function proxyJson(
  request: NextRequest,
  path: string,
  fallbackMessage: string,
  method = request.method
) {
  try {
    const headers: HeadersInit = {};
    let body: string | undefined;

    if (!["GET", "HEAD", "DELETE"].includes(method)) {
      body = await request.text();
      headers["Content-Type"] = request.headers.get("Content-Type") || "application/json";
    }

    const response = await fetch(toBackendUrl(path, request.nextUrl.search), {
      method,
      headers,
      body,
      cache: "no-store"
    });

    return await toJsonResponse(response, fallbackMessage);
  } catch (error) {
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? `Python backend request failed: ${error.message}`
            : "Python backend request failed"
      },
      { status: 502 }
    );
  }
}

export async function proxyJsonNoRequest(path: string, fallbackMessage: string, method = "GET") {
  try {
    const response = await fetch(toBackendUrl(path), {
      method,
      cache: "no-store"
    });

    return await toJsonResponse(response, fallbackMessage);
  } catch (error) {
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? `Python backend request failed: ${error.message}`
            : "Python backend request failed"
      },
      { status: 502 }
    );
  }
}

export async function proxyDownload(path: string, filename: string, fallbackMessage: string) {
  try {
    const response = await fetch(toBackendUrl(path), {
      cache: "no-store"
    });
    const text = await response.text();

    if (!response.ok) {
      let payload: unknown = null;
      try {
        payload = text ? (JSON.parse(text) as unknown) : null;
      } catch {
        payload = null;
      }
      return NextResponse.json(
        { error: backendError(payload, fallbackMessage) },
        { status: response.status }
      );
    }

    const payload = text ? JSON.parse(text) : null;
    return new NextResponse(JSON.stringify(payload, null, 2), {
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Content-Disposition": `attachment; filename="${filename}"`
      }
    });
  } catch (error) {
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? `Python backend request failed: ${error.message}`
            : "Python backend request failed"
      },
      { status: 502 }
    );
  }
}
