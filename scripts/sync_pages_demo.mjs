import { cp, mkdir, readdir, readFile, unlink, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const buildDir = path.join(root, '.cache', 'lkaya-pages-build')
const targetDir = path.join(root, 'lkaya-pages')
const sourceAssets = path.join(buildDir, 'assets')
const targetAssets = path.join(targetDir, 'assets')

const buildIndex = await readFile(path.join(buildDir, 'index.html'), 'utf8')
const js = buildIndex.match(/src="(\/assets\/index-[^"]+\.js)"/)?.[1]
const css = buildIndex.match(/href="(\/assets\/index-[^"]+\.css)"/)?.[1]
if (!js || !css) throw new Error('Could not find built JS/CSS asset paths')

await mkdir(targetAssets, { recursive: true })
const builtAssets = await readdir(sourceAssets)
for (const name of builtAssets) {
  await cp(path.join(sourceAssets, name), path.join(targetAssets, name), { force: true })
}

for (const entry of await readdir(targetAssets, { withFileTypes: true })) {
  if (entry.isFile() && !builtAssets.includes(entry.name)) {
    await unlink(path.join(targetAssets, entry.name))
  }
}

const moduleTag = buildIndex.match(/<script type="module"[^>]*><\/script>/)?.[0]
if (!moduleTag) throw new Error('Could not find built module entry')

const pagesHtml = buildIndex.replace(
  moduleTag,
  `<script src="/mock-api.js"></script>\n    ${moduleTag}`
)
for (const name of ['index.html', '404.html']) {
  await writeFile(path.join(targetDir, name), pagesHtml, 'utf8')
}

console.log(`Synced Cloudflare Pages demo: ${js}, ${css}`)
