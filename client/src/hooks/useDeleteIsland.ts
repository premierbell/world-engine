import { useMutation, useQueryClient } from '@tanstack/react-query';
import { deleteIsland } from '../api/island';

export function useDeleteIsland() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (islandId: number) => deleteIsland(islandId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['islands'] });
      // 삭제된 섬의 스크랩은 서버에서 islandId가 비워져 "정리할
      // 스크랩"으로 돌아간다 - 스크랩 목록도 같이 갱신.
      queryClient.invalidateQueries({ queryKey: ['scraps'] });
    },
  });
}
