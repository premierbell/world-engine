import { useMutation, useQueryClient } from '@tanstack/react-query';
import { deleteTopic } from '../api/topic';

export function useDeleteTopic(islandId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (topicId: number) => deleteTopic(topicId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['island', islandId] });
      // 지도(MapView)는 건물 개수/위치를 islands 목록의 topicIds로
      // 그린다(client/src/islandGrowth/) - island 쿼리만 갱신하면 패널
      // 안 목록은 바뀌어도 지도 위 건물은 그대로 남는다(실제 클릭
      // 테스트로 발견). 두 쿼리 다 갱신해야 지도까지 같이 바뀐다.
      queryClient.invalidateQueries({ queryKey: ['islands'] });
    },
  });
}
