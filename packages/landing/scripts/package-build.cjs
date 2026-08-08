// scripts/package-build.cjs — package the project as a tarball for Vercel upload
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const projectRoot = path.resolve(__dirname, '..');
process.chdir(projectRoot);

console.log('--- building dist/ ---');
execSync('npm run build', { stdio: 'inherit' });

console.log('--- creating full project tarball ---');
const tarPath = path.join(projectRoot, 'project.tgz');
if (fs.existsSync(tarPath)) fs.unlinkSync(tarPath);

// Exclude heavy / ephemeral / sensitive paths. Vercel will re-run npm install
// (so node_modules is fine to skip), .env must NOT be in the tarball.
const excludes = [
  '--exclude=node_modules',
  '--exclude=.next',
  '--exclude=dist',
  '--exclude=.vercel',
  '--exclude=out',
  '--exclude=.git',
  '--exclude=*.log',
  '--exclude=.env',
  '--exclude=.env.*',
  'project.tgz', // exclude the tarball itself
];
const excludeStr = excludes.join(' ');
execSync(`tar -czf project.tgz ${excludeStr} --exclude-from=<(git ls-files --others --exclude-standard | sed 's/^/--exclude=/') 2>/dev/null || tar -czf project.tgz ${excludeStr} .`, { stdio: 'inherit', shell: '/bin/bash' });

const stat = fs.statSync(tarPath);
console.log(`project.tgz: ${(stat.size / 1024 / 1024).toFixed(2)} MB`);

