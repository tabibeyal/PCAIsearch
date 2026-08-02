import { BANNER_CONTENT_TYPE, BANNER_SIZE, renderBanner } from './banner';

export const alt = 'Ask the Pali Canon — type a question, find the suttas that answer it.';
export const size = BANNER_SIZE;
export const contentType = BANNER_CONTENT_TYPE;

export default async function OpengraphImage() {
  return renderBanner();
}
