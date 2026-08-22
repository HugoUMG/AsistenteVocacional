// Check del ritmo sin voz: saca las dos funciones tocadas del Chat.jsx real y
// las corre. Falla si el silencio vuelve a ser fijo o si mutear cuelga el turno.
import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'

const CR = String.fromCharCode(13)
const src = readFileSync(import.meta.dirname + '/src/Chat.jsx', 'utf8').split(CR).join('')
const sacar = (firma) => {
  const i = src.indexOf(firma)
  assert.ok(i > 0, 'no encontre ' + firma)
  const fin = src.indexOf('\n}\n', i)
  assert.ok(fin > i, 'no encontre el cierre de ' + firma)
  return src.slice(i, fin + 3)
}

const velocidad = 1
const { tiempoLectura, reproducirUrl } = new Function(
  'velocidad', 'Audio',
  sacar('function tiempoLectura(') + '\n' + sacar('function reproducirUrl(') +
  '\nreturn { tiempoLectura, reproducirUrl }'
)(velocidad, function FakeAudio() {
  return globalThis.__audio
})

// 1) El tiempo crece con el texto y respeta los topes.
const corta = tiempoLectura('Hola.')
const larga = tiempoLectura('Contame '.repeat(40))
assert.ok(larga > corta, 'una frase larga debe durar mas que una corta')
assert.equal(corta, 900, 'piso de 900 ms')
assert.equal(larga, 9000, 'techo de 9000 ms')
assert.equal(tiempoLectura('una dos tres cuatro cinco'), 2000)
assert.equal(tiempoLectura(''), 900)

// 2) Mutear a media lectura resuelve el turno en vez de colgarlo.
globalThis.__audio = {
  play() { return Promise.resolve() },
  pause() { this.onpause && this.onpause() },
}
const turno = reproducirUrl('blob:x')
setTimeout(() => globalThis.__audio.pause(), 10)
const colgado = new Promise((_, rej) =>
  setTimeout(() => rej(new Error('el turno quedo colgado al mutear')), 500))
await Promise.race([turno, colgado])

const media = tiempoLectura('Contame que materia se te hace mas facil en el colegio.')
console.log('ok  corta=' + corta + 'ms  media=' + media + 'ms  larga=' + larga + 'ms')
