const sharp = require('sharp');
const toIco = require('to-ico');
const path = require('path');
const fs = require('fs');

const SVG_PATH = path.join(__dirname, '../frontend/public/icon.svg');
const OUT_DIR = path.join(__dirname, '../frontend/public');

async function main() {
  const svgBuffer = fs.readFileSync(SVG_PATH);

  const pngSizes = [
    { name: 'apple-touch-icon.png', size: 180 },
    { name: 'icon-192.png', size: 192 },
    { name: 'icon-512.png', size: 512 },
  ];

  for (const { name, size } of pngSizes) {
    await sharp(svgBuffer)
      .resize(size, size)
      .png()
      .toFile(path.join(OUT_DIR, name));
    console.log(`✓ ${name} (${size}×${size})`);
  }

  const ico32 = await sharp(svgBuffer).resize(32, 32).png().toBuffer();
  const icoBuffer = await toIco([ico32]);
  fs.writeFileSync(path.join(OUT_DIR, 'favicon.ico'), icoBuffer);
  console.log('✓ favicon.ico (32×32)');
}

main().catch((err) => { console.error(err); process.exit(1); });
