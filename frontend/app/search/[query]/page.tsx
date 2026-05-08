import React from 'react';
import { getSynthesis } from '@/lib/api';
import { DualPaneContainer } from '@/components/deep-dive/DualPaneContainer';
import { SynthesisResponse } from '@/types/api';

async function SearchPage({ params }: { params: { query: string } }) {
  const query = decodeURIComponent(params.query);

  try {
    const data: SynthesisResponse = await getSynthesis(query);

    return (
      <main className="h-screen w-full">
        <DualPaneContainer data={data} />
      </main>
    );
  } catch (error) {
    return (
      <div className="h-screen flex items-center justify-center text-red-500 p-4 text-center">
        <div>
          <h1 className="text-2xl font-bold mb-2">Search Error</h1>
          <p>Unable to retrieve synthesis for this query. Please check if the backend is running.</p>
          <a href="/" className="mt-4 inline-block text-blue-600 underline">Return to home</a>
        </div>
      </div>
    );
  }
}

export default SearchPage;
