/**
 * Copies vendor scripts and fontsource WOFF2 assets into static/vendor/ and static/fonts/
 * Ensures 100% self-hosted, offline-ready runtime with zero external CDN dependencies.
 */
const fs = require('fs');
const path = require('path');

const rootDir = path.join(__dirname, '..');
const vendorDest = path.join(rootDir, 'static', 'vendor');
const fontsDest = path.join(rootDir, 'static', 'fonts');

[vendorDest, fontsDest].forEach((dir) => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
});

const vendorFiles = [
  { src: 'node_modules/htmx.org/dist/htmx.min.js', dest: path.join(vendorDest, 'htmx.min.js') },
  { src: 'node_modules/alpinejs/dist/cdn.min.js', dest: path.join(vendorDest, 'alpine.min.js') },
  { src: 'node_modules/gsap/dist/gsap.min.js', dest: path.join(vendorDest, 'gsap.min.js') },
  { src: 'node_modules/gsap/dist/ScrollTrigger.min.js', dest: path.join(vendorDest, 'ScrollTrigger.min.js') },
  { src: 'node_modules/gsap/dist/Flip.min.js', dest: path.join(vendorDest, 'Flip.min.js') }
];

const fontFiles = [
  // Inter
  { src: 'node_modules/@fontsource/inter/files/inter-latin-400-normal.woff2', dest: path.join(fontsDest, 'inter-latin-400-normal.woff2') },
  { src: 'node_modules/@fontsource/inter/files/inter-latin-500-normal.woff2', dest: path.join(fontsDest, 'inter-latin-500-normal.woff2') },
  { src: 'node_modules/@fontsource/inter/files/inter-latin-600-normal.woff2', dest: path.join(fontsDest, 'inter-latin-600-normal.woff2') },
  { src: 'node_modules/@fontsource/inter/files/inter-latin-700-normal.woff2', dest: path.join(fontsDest, 'inter-latin-700-normal.woff2') },
  // Fraunces
  { src: 'node_modules/@fontsource/fraunces/files/fraunces-latin-600-normal.woff2', dest: path.join(fontsDest, 'fraunces-latin-600-normal.woff2') },
  { src: 'node_modules/@fontsource/fraunces/files/fraunces-latin-700-normal.woff2', dest: path.join(fontsDest, 'fraunces-latin-700-normal.woff2') },
  // JetBrains Mono
  { src: 'node_modules/@fontsource/jetbrains-mono/files/jetbrains-mono-latin-400-normal.woff2', dest: path.join(fontsDest, 'jetbrains-mono-latin-400-normal.woff2') },
  { src: 'node_modules/@fontsource/jetbrains-mono/files/jetbrains-mono-latin-500-normal.woff2', dest: path.join(fontsDest, 'jetbrains-mono-latin-500-normal.woff2') },
  { src: 'node_modules/@fontsource/jetbrains-mono/files/jetbrains-mono-latin-600-normal.woff2', dest: path.join(fontsDest, 'jetbrains-mono-latin-600-normal.woff2') }
];

[...vendorFiles, ...fontFiles].forEach((file) => {
  const srcPath = path.join(rootDir, file.src);
  if (fs.existsSync(srcPath)) {
    fs.copyFileSync(srcPath, file.dest);
    console.log(`Copied ${file.src} -> ${path.relative(rootDir, file.dest)}`);
  } else {
    console.warn(`Source asset ${file.src} not found. Run npm install.`);
  }
});
