import { initializeApp, getApps, type FirebaseApp } from 'firebase/app'
import { getFirestore, type Firestore } from 'firebase/firestore'
import { getAuth, type Auth } from 'firebase/auth'
import { getFirebaseConfig } from '@/config/firebaseDefaults'

const COLLECTION_DATOS = 'kisvic_datos'

let app: FirebaseApp | null = null
let db: Firestore | null = null
let auth: Auth | null = null

export function initFirebase(): { app: FirebaseApp; db: Firestore; auth: Auth } | null {
  const config = getFirebaseConfig()
  if (!config.apiKey || !config.projectId) {
    return null
  }
  if (!app) {
    app = getApps().length ? getApps()[0]! : initializeApp(config)
    db = getFirestore(app)
    auth = getAuth(app)
  }
  return { app, db: db!, auth: auth! }
}

export function getDb(): Firestore | null {
  if (!db) initFirebase()
  return db
}

export function getAuthInstance(): Auth | null {
  if (!auth) initFirebase()
  return auth
}

export { COLLECTION_DATOS }
