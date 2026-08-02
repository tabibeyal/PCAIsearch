import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

import { ImageResponse } from 'next/og';

import { formatQuestionForBanner } from '@/lib/bannerQuestion';

export const BANNER_SIZE = { width: 1200, height: 630 } as const;
export const BANNER_CONTENT_TYPE = 'image/png' as const;

const SITE_NAME = 'Ask the Pali Canon';
const TAGLINE = 'Type a question or topic — find the suttas that answer it.';
const HOME_EXAMPLE = 'What did the Buddha say about anger?';

// Palette lifted from public/icon.svg so the rings match the favicon mark.
const BG_CHARCOAL = '#1c1611';
const TEXT_PRIMARY = '#faf9f7';
const TEXT_SECONDARY = '#d6c7b3';
const TEXT_QUESTION = '#fde68a';
const AMBER_OUTER = '#fcd34d';
const AMBER_MID = '#d97706';
const AMBER_INNER = '#b45309';

const FONT_PATH = join(process.cwd(), 'public/fonts/Inter-Regular.otf');

export type BannerExample = {
  exampleQuestion: string;
  alt: string;
};

const HOME_EXAMPLE_BANNER: BannerExample = {
  exampleQuestion: HOME_EXAMPLE,
  alt: 'Ask the Pali Canon — homepage banner with an example question about anger.',
};

export async function renderBanner(example: BannerExample = HOME_EXAMPLE_BANNER) {
  const displayQuestion = formatQuestionForBanner(example.exampleQuestion);
  const fontData = await readFile(FONT_PATH);

  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: BG_CHARCOAL,
          color: TEXT_PRIMARY,
          padding: '72px 80px',
        }}
      >
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            flexGrow: 1,
            justifyContent: 'center',
            maxWidth: 880,
          }}
        >
          <div
            style={{
              fontSize: 80,
              fontWeight: 400,
              lineHeight: 1.1,
              color: TEXT_PRIMARY,
              display: 'flex',
            }}
          >
            {SITE_NAME}
          </div>
          <div
            style={{
              fontSize: 30,
              fontWeight: 400,
              lineHeight: 1.4,
              color: TEXT_SECONDARY,
              marginTop: 24,
              display: 'flex',
            }}
          >
            {TAGLINE}
          </div>
          <div
            style={{
              marginTop: 48,
              paddingTop: 24,
              paddingBottom: 24,
              paddingLeft: 32,
              paddingRight: 32,
              borderLeftWidth: 4,
              borderLeftStyle: 'solid',
              borderLeftColor: AMBER_MID,
              display: 'flex',
            }}
          >
            <div
              style={{
                fontSize: 36,
                fontWeight: 400,
                lineHeight: 1.3,
                color: TEXT_QUESTION,
                display: 'flex',
              }}
            >
              {displayQuestion}
            </div>
          </div>
        </div>
        <div
          style={{
            position: 'absolute',
            right: 60,
            bottom: 40,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <div
            style={{
              width: 96,
              height: 96,
              borderRadius: 9999,
              borderWidth: 4,
              borderStyle: 'solid',
              borderColor: AMBER_OUTER,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <div
              style={{
                width: 64,
                height: 64,
                borderRadius: 9999,
                borderWidth: 6,
                borderStyle: 'solid',
                borderColor: AMBER_MID,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <div
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: 9999,
                  backgroundColor: AMBER_INNER,
                  display: 'flex',
                }}
              />
            </div>
          </div>
        </div>
      </div>
    ),
    {
      ...BANNER_SIZE,
      fonts: [
        { name: 'Inter', data: fontData, style: 'normal', weight: 400 },
      ],
    },
  );
}
