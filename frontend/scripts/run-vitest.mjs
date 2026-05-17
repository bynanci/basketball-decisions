#!/usr/bin/env node
import { spawnSync } from 'node:child_process'

const incomingArgs = process.argv.slice(2)
const vitestArgs = []
let requestedRunInBand = false

for (const arg of incomingArgs) {
  if (arg === '--runInBand' || arg === '-i') {
    requestedRunInBand = true
    continue
  }
  vitestArgs.push(arg)
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
