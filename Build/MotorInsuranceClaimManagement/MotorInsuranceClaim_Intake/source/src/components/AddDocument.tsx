import { useState } from 'react'
import type { FormEvent } from 'react'
import type { UiPath } from '@uipath/uipath-typescript/core'
import { Alert, AlertDescription } from '@uipath/apollo-wind/components/ui/alert'
import { Button } from '@uipath/apollo-wind/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@uipath/apollo-wind/components/ui/card'
import { Input } from '@uipath/apollo-wind/components/ui/input'
import { Label } from '@uipath/apollo-wind/components/ui/label'
import { addSupplementalDocument } from '../lib/intake'
import type { Workspace } from '../lib/intake'

export function AddDocument({ sdk, ws }: { sdk: UiPath; ws: Workspace }) {
  const [claimId, setClaimId] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState('')
  const [error, setError] = useState('')
  const [done, setDone] = useState('')
  const [resetKey, setResetKey] = useState(0)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setDone('')
    if (!file) {
      setError('Please choose a document.')
      return
    }
    setBusy(true)
    try {
      await addSupplementalDocument(sdk, ws, claimId.trim(), file, setProgress)
      setDone(`Document received for ${claimId.trim()}. The case will pick it up.`)
      setClaimId('')
      setFile(null)
      setResetKey((k) => k + 1)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
      setProgress('')
    }
  }

  return (
    <Card className="mx-auto w-full max-w-xl">
      <CardHeader>
        <CardTitle>Add a document to an existing claim</CardTitle>
        <CardDescription>
          This is the customer reply: upload the document we asked for. The claim is marked as received so the case can resume.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form key={resetKey} onSubmit={submit} className="space-y-4">
          <div className="space-y-1">
            <Label htmlFor="claimId2">Your claim number (from your confirmation)</Label>
            <Input id="claimId2" required placeholder="CLM-1002" value={claimId} onChange={(e) => setClaimId(e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="suppFile">Document</Label>
            <Input id="suppFile" type="file" accept="application/pdf,image/*" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </div>
          {error && (
            <Alert variant="destructive">
              <AlertDescription className="break-words">{error}</AlertDescription>
            </Alert>
          )}
          {done && (
            <Alert>
              <AlertDescription className="break-words">{done}</AlertDescription>
            </Alert>
          )}
          {busy && <p className="text-sm text-muted-foreground">{progress || 'Working...'}</p>}
          <Button type="submit" disabled={busy}>
            {busy ? 'Sending...' : 'Send document'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
