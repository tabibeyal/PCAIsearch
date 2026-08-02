import { BANNER_CONTENT_TYPE, BANNER_SIZE, renderBanner } from '@/app/banner';
import { getSharedAnswer } from '@/lib/api';

// Per-request so platforms get a fresh image per share id; otherwise Next
// would try to enumerate every id at build time.
export const dynamic = 'force-dynamic';
export const alt = 'Ask the Pali Canon — shared answer preview.';
export const size = BANNER_SIZE;
export const contentType = BANNER_CONTENT_TYPE;

export default async function ShareOpengraphImage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  try {
    const shared = await getSharedAnswer(id);
    return renderBanner({
      exampleQuestion: shared.query,
      alt: `Ask the Pali Canon — answer to "${shared.query}".`,
    });
  } catch {
    // Unknown / deleted / malformed share id: fall back to the generic
    // homepage banner so the link still renders a sensible preview.
    return renderBanner();
  }
}
