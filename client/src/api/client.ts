export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export async function apiFetch<T>(input: string, init?: RequestInit): Promise<T> {
  const response = await fetch(input, {
    ...init,
    headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, body?.message ?? `요청 실패: ${response.status}`);
  }

  // DELETE 같은 void 응답은 본문이 아예 없다(Content-Length: 0) -
  // response.json()을 그대로 부르면 빈 문자열 파싱 실패로 죽는다.
  // 실제 curl로 DELETE /api/islands/{id} 응답을 확인하다가 발견.
  if (response.status === 204 || response.headers.get('content-length') === '0') {
    return undefined as T;
  }

  return response.json();
}
