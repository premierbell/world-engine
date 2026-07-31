import { useMutation } from '@tanstack/react-query';
import { refreshRecommendations } from '../api/scrap';

export function useRefreshRecommendations() {
  return useMutation({
    mutationFn: (scrapId: number) => refreshRecommendations(scrapId),
  });
}
