import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { HomePage } from './pages/HomePage';
import { NotFoundPage } from './pages/NotFoundPage';

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* 지도(HomePage)는 두 경로 모두에서 같은 컴포넌트로 마운트된 채 유지된다 -
              /islands/:id는 페이지 전환이 아니라 지도 위에 Island 패널을 여는 것뿐이다.
              docs/map_home_redesign.md "라우팅 변경" 참고. */}
          <Route path="/" element={<HomePage />} />
          <Route path="/islands/:id" element={<HomePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
