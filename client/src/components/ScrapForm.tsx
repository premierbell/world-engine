import { useState, type FormEvent } from 'react';

interface ScrapFormProps {
  onSubmit: (url: string, userContext: string) => void;
}

export function ScrapForm({ onSubmit }: ScrapFormProps) {
  const [url, setUrl] = useState('');
  const [context, setContext] = useState('');

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit(url, context);
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="url"
        placeholder="https://..."
        required
        value={url}
        onChange={(event) => setUrl(event.target.value)}
      />
      <input
        type="text"
        placeholder="왜 저장했나요? (선택)"
        value={context}
        onChange={(event) => setContext(event.target.value)}
      />
      <button type="submit">스크랩</button>
    </form>
  );
}
