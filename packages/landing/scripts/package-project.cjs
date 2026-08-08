// scripts/package-project.cjs — create a proper tarball for Vercel upload
const { createWriteStream } = require('fs');
const { createGzip } = require('zlib');
const { resolve, relative, join, sep } = require('path');
const { createReadStream, statSync, readdirSync, statSync: _stat } = require('fs');
const tar = require('tar');
const { pipeline } = require('stream/promises');

const projectRoot = resolve(__dirname, '..');
const tarPath = join(projectRoot, 'project.tgz');

const EXCLUDE_DIRS = new Set(['node_modules', '.next', 'dist', '.vercel', 'out', '.git']);
const EXCLUDE_FILES = new Set(['.env']);
const EXCLUDE_PATTERNS = [/\.log$/, /project\.tgz$/, /scripts[\\/](?:package-project|package-build|vercel-upload-deploy)\.cjs$/];

function shouldInclude(rel) {
  const parts = rel.split(/[\\/]/);
  for (const p of parts) if (EXCLUDE_DIRS.has(p)) return false;
  for (const p of parts) if (EXCLUDE_FILES.has(p)) return false;
  for (const r of EXCLUDE_PATTERNS) if (r.test(rel)) return false;
  return true;
}

async function main() {
  // Use tar pack from a list of files
  const allFiles = [];
  function walk(dir) {
    for (const name of readdirSync(dir)) {
      const full = join(dir, name);
      const rel = relative(projectRoot, full).split(sep).join('/');
      if (!shouldInclude(rel)) continue;
      const st = statSync(full);
      if (st.isDirectory()) {
        walk(full);
      } else if (st.isFile()) {
        allFiles.push(rel);
      }
    }
  }
  walk(projectRoot);

  console.log(`Including ${allFiles.length} files`);
  // Sanity: ensure package.json is at the top
  if (!allFiles.includes('package.json')) {
    console.error('ERROR: package.json not included!');
    process.exit(1);
  }

  await tar.c(
    {
      gzip: true,
      file: tarPath,
      cwd: projectRoot,
      portable: true,
    },
    allFiles
  );

  const { statSync: statFs } = require('fs');
  const sz = statFs(tarPath).size;
  console.log(`project.tgz: ${(sz / 1024 / 1024).toFixed(2)} MB`);
}

main().catch((e) => { console.error(e); process.exit(1); });
