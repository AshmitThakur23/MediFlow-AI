import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import express from 'express'
import { apiRouter } from './server/routes.ts'
import { seedDemoData } from './server/store.ts'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PORT = Number.parseInt(process.env.PORT ?? '3000', 10) || 3000
const API_V1_PREFIX = process.env.API_V1_PREFIX || '/api/v1'
const ROOT_DIR = __dirname
const DIST_DIR = path.resolve(ROOT_DIR, 'dist')

seedDemoData()

async function createApp() {
  const app = express()
  app.use(express.json({ limit: '2mb' }))

  app.use(API_V1_PREFIX, apiRouter)

  const useProductionStatic =
    process.env.NODE_ENV === 'production' &&
    fs.existsSync(path.join(DIST_DIR, 'index.html'))

  if (useProductionStatic) {
    app.use(express.static(DIST_DIR))
    app.use((req, res, next) => {
      if (req.method === 'GET' && !req.path.startsWith('/api/')) {
        res.sendFile(path.join(DIST_DIR, 'index.html'))
        return
      }
      next()
    })
  } else {
    const { createServer: createViteServer } = await import('vite')
    const vite = await createViteServer({
      root: ROOT_DIR,
      configFile: path.join(ROOT_DIR, 'vite.config.ts'),
      server: {
        middlewareMode: true,
        hmr: false,
      },
      appType: 'spa',
    })
    app.use(vite.middlewares)
  }

  return app
}

createApp()
  .then((app) => {
    app.listen(PORT, '0.0.0.0', () => {
      console.log(`MediFlow AI server listening on http://0.0.0.0:${PORT}`)
    })
  })
  .catch((error) => {
    console.error('Failed to start MediFlow AI server:', error)
    process.exit(1)
  })
