#!/usr/bin/env node
import { spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, relative, resolve, sep } from 'node:path'

const incomingArgs = process.argv.slice(2)
const scriptDir = dirname(fileURLToPath(import.meta.url))
const frontendRoot = resolve(scriptDir, '..')
const repoRoot = resolve(frontendRoot, '..')
const vitestArgs = []
let requestedRunInBand = false

function normalizePathFilter(arg) {
  if (arg.startsWith('-')) {
    return arg
  }

  const absoluteFromRepo = resolve(repoRoot, arg)
  if (absoluteFromRepo.startsWith(`${frontendRoot}${sep}`) && existsSync(absoluteFromRepo)) {
    return relative(frontendRoot, absoluteFromRepo)
  }

  return arg
}

for (const arg of incomingArgs) {
  if (arg === '--runInBand' || arg === '-i') {
    requestedRunInBand = true
    continue
  }
  vitestArgs.push(normalizePathFilter(arg))
}

if (requestedRunInBand) {
  if (!vitestArgs.includes('--no-file-parallelism')) {
    vitestArgs.push('--no-file-parallelism')
  }
  if (!vitestArgs.some((arg) => arg === '--maxWorkers' || arg.startsWith('--maxWorkers='))) {
    vitestArgs.push('--maxWorkers=1')
  }
}

const command = process.platform === 'win32' ? 'vitest.cmd' : 'vitest'
const result = spawnSync(command, ['run', ...vitestArgs], { stdio: 'inherit' })

if (result.error) {
  console.error(result.error.message)
  process.exit(1)
}

process.exit(result.status ?? 1)
