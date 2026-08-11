import { apiFetch } from './client';
import type { WorldExportResponse } from '../types/export';

export function fetchWorldExport() {
  return apiFetch<WorldExportResponse>('/api/export');
}
