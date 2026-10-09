import { useEffect, useState } from 'react'
import { FilePlus2, FileText, LogOut, ShieldCheck } from 'lucide-react'
import { Alert, AlertDescription } from '@uipath/apollo-wind/components/ui/alert'
import { Button } from '@uipath/apollo-wind/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@uipath/apollo-wind/components/ui/card'
import { Spinner } from '@uipath/apollo-wind/components/ui/spinner'
import { AuthProvider, useAuth } from './hooks/useAuth'
import { ThemeToggle } from './components/Theme'
import { NewClaim } from './components/NewClaim'
import { AddDocument } from './components/AddDocument'
import { findWorkspaces } from './lib/intake'
import type { Workspace } from './lib/intake'

type View = 'new' | 'add'

function AppContent() {
  const { isAuthenticated, isLoading, login, logout, error, sdk } = useAuth()
  const [workspaces, setWorkspaces] = useState<Workspace[] | null>(null)
  // null = nothing chosen yet. With several workspaces the user MUST choose; we never default silently.
  const [chosen, setChosen] = useState<number | null>(null)
  const [wsError, setWsError] = useState('')
  const [view, setView] = useState<View>('new')
  const ws = workspaces && chosen !== null ? workspaces[chosen] : null

  useEffect(() => {
    if (!isAuthenticated) return
    let cancelled = false
    findWorkspaces(sdk)
      .then((w) => {
        if (cancelled) return
        setWorkspaces(w)
        if (w.length === 1) setChosen(0)
      })
      .catch((e) => !cancelled && setWsError(e instanceof Error ? e.message : String(e)))
    return () => {
      cancelled = true
    }
  }, [isAuthenticated, sdk])

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner label="Initializing UiPath SDK..." showLabel />
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <Card className="w-full max-w-sm">
          <CardHeader className="items-center text-center">
            <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <CardTitle>Claims intake</CardTitle>
            <CardDescription>Sign in with your UiPath account to register a claim.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <Button onClick={login} className="w-full">
              Sign in with UiPath
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="flex items-center justify-between gap-4 border-b px-4 py-3 sm:px-6">
        <div className="flex min-w-0 items-center gap-2">
          <FileText className="h-5 w-5 shrink-0 text-primary" />
          <h1 className="truncate text-base font-semibold">Motor Insurance Claim Intake</h1>
        </div>
        <div className="flex items-center gap-2">
          <Button variant={view === 'new' ? 'default' : 'ghost'} size="sm" onClick={() => setView('new')}>
            <FilePlus2 className="h-4 w-4" />
            <span className="hidden sm:inline">New claim</span>
          </Button>
          <Button variant={view === 'add' ? 'default' : 'ghost'} size="sm" onClick={() => setView('add')}>
            <span>Add document</span>
          </Button>
          <ThemeToggle />
          <Button variant="ghost" size="sm" onClick={logout}>
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:inline">Sign out</span>
          </Button>
        </div>
      </header>
      <main className="flex-1 p-4 sm:p-6">
        {wsError && (
          <Alert variant="destructive" className="mx-auto mb-4 max-w-3xl">
            <AlertDescription className="break-words">{wsError}</AlertDescription>
          </Alert>
        )}
        {!ws && !wsError && (
          <div className="flex justify-center p-8">
            <Spinner label="Finding the claims workspace..." showLabel />
          </div>
        )}
        {workspaces && (
          <div className="mx-auto mb-4 max-w-3xl space-y-2 text-xs text-muted-foreground">
            {workspaces.length > 1 ? (
              <>
                <p className="text-sm font-medium text-foreground">
                  More than one claims workspace was found. Choose where claims are stored:
                </p>
                <select
                  className="w-full rounded-md border bg-background p-2 text-sm text-foreground"
                  value={chosen === null ? '' : String(chosen)}
                  onChange={(e) => setChosen(e.target.value === '' ? null : Number(e.target.value))}
                >
                  <option value="">Select a workspace...</option>
                  {workspaces.map((w, i) => (
                    <option key={w.entityId + w.folderKey} value={String(i)}>
                      {w.label}
                    </option>
                  ))}
                </select>
              </>
            ) : (
              ws && <p>Storing claims in: {ws.label}</p>
            )}
          </div>
        )}
        {ws && (view === 'new' ? <NewClaim key={ws.entityId} sdk={sdk} ws={ws} /> : <AddDocument key={ws.entityId} sdk={sdk} ws={ws} />)}
      </main>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}
