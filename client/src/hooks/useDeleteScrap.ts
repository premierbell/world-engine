import { useMutation, useQueryClient } from '@tanstack/react-query';
import { deleteScrap } from '../api/scrap';

export function useDeleteScrap() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteScrap(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scraps'] });
      // useDeleteTopic과 같은 이유 - 확정된 스크랩을 지우면 지도 건물
      // 개수(islands 쿼리의 topicIds 기반)도 바뀔 수 있어서 같이 갱신.
      queryClient.invalidateQueries({ queryKey: ['islands'] });
    },
  });
}
