/** Hostnames de Firebase Hosting donde se usa la config oficial del proyecto. */
export const OFFICIAL_FIREBASE_HOSTNAMES = [
  'kisvic-facturacion.web.app',
  'kisvic-facturacion.firebaseapp.com',
  'localhost',
  '127.0.0.1',
]

export function getResolvedOfficialHostnames(): string[] {
  const base = OFFICIAL_FIREBASE_HOSTNAMES.map((h) => h.toLowerCase())
  const raw = import.meta.env?.VITE_FIREBASE_OFFICIAL_HOSTS ?? ''
  const extra = String(raw)
    .split(',')
    .map((h) => h.trim().toLowerCase())
    .filter(Boolean)
  return [...new Set([...base, ...extra])]
}

/** Config por defecto: rellena .env.production o variables VITE_FIREBASE_* */
export function getFirebaseConfig() {
  const hostname = typeof window !== 'undefined' ? window.location.hostname.toLowerCase() : ''
  const official = getResolvedOfficialHostnames()

  const fromEnv = {
    apiKey: import.meta.env.VITE_FIREBASE_API_KEY as string | undefined,
    authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN as string | undefined,
    projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID as string | undefined,
    storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET as string | undefined,
    messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID as string | undefined,
    appId: import.meta.env.VITE_FIREBASE_APP_ID as string | undefined,
  }

  if (fromEnv.apiKey && fromEnv.projectId) {
    return {
      apiKey: fromEnv.apiKey,
      authDomain: fromEnv.authDomain || `${fromEnv.projectId}.firebaseapp.com`,
      projectId: fromEnv.projectId,
      storageBucket: fromEnv.storageBucket || `${fromEnv.projectId}.appspot.com`,
      messagingSenderId: fromEnv.messagingSenderId || '',
      appId: fromEnv.appId || '',
    }
  }

  if (hostname && official.includes(hostname)) {
    console.warn(
      '[Firebase] Falta .env.production con VITE_FIREBASE_*. Crea la app Web en la consola de Firebase.',
    )
  }

  return {
    apiKey: '',
    authDomain: 'kisvic-facturacion.firebaseapp.com',
    projectId: 'kisvic-facturacion',
    storageBucket: 'kisvic-facturacion.firebasestorage.app',
    messagingSenderId: '',
    appId: '',
  }
}
