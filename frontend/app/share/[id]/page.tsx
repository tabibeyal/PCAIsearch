import { notFound } from 'next/navigation';
import { getSharedAnswer } from '@/lib/api';
import { ShareView } from '@/components/deep-dive/ShareView';

export default async function SharePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  let shared;
  try {
    shared = await getSharedAnswer(id);
  } catch (e) {
    if ((e as { status?: number }).status === 404) notFound();
    throw e;
  }

  return <ShareView query={shared.query} answer={shared.answer} context={shared.context} />;
}
