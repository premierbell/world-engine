import { useMutation } from '@tanstack/react-query';
import { generateTopicCandidates } from '../api/island';

export function useGenerateTopicCandidates() {
  return useMutation({
    mutationFn: (islandId: number) => generateTopicCandidates(islandId),
  });
}
