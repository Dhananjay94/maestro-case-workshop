import { useState } from 'react'
import type { FormEvent } from 'react'
import type { UiPath } from '@uipath/uipath-typescript/core'
import { Alert, AlertDescription } from '@uipath/apollo-wind/components/ui/alert'
import { Button } from '@uipath/apollo-wind/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@uipath/apollo-wind/components/ui/card'
import { Input } from '@uipath/apollo-wind/components/ui/input'
import { Label } from '@uipath/apollo-wind/components/ui/label'
import { Textarea } from '@uipath/apollo-wind/components/ui/textarea'
import { DOCUMENT_SLOTS, createClaim } from '../lib/intake'
import type { ClaimForm, SlotKey, Workspace } from '../lib/intake'

const EMPTY: ClaimForm = {
  customerName: '',
  policyNumber: '',
  vehicleRegistration: '',
  vehicleModel: '',
  incidentDate: '',
  claimAmount: '',
  incidentDescription: '',
}

export function NewClaim({ sdk, ws }: { sdk: UiPath; ws: Workspace }) {
  const [form, setForm] = useState<ClaimForm>(EMPTY)
  const [files, setFiles] = useState<Partial<Record<SlotKey, File>>>({})
  // Bumping a slot's counter remounts its file input, which is how a chosen file is cleared.
  const [resets, setResets] = useState<Record<string, number>>({})
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState('')
  const [error, setError] = useState('')
  const [done, setDone] = useState('')
  const [resetKey, setResetKey] = useState(0)

  const set = (k: keyof ClaimForm) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }))

  const missingRequired = DOCUMENT_SLOTS.filter((s) => s.required && !files[s.key])

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setDone('')
    if (missingRequired.length > 0) {
      setError(`Please attach: ${missingRequired.map((s) => s.label).join(', ')}`)
      return
    }
    setBusy(true)
    try {
      const id = await createClaim(sdk, ws, form, files, setProgress)
      setDone(`Claim registered successfully. Your claim number is ${id}. Please keep it to send any further documents.`)
      setForm(EMPTY)
      setFiles({})
      setResets((r) => Object.fromEntries(DOCUMENT_SLOTS.map((s) => [s.key, (r[s.key] ?? 0) + 1])))
      setResetKey((k) => k + 1)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
      setProgress('')
    }
  }

  return (
    <Card className="mx-auto w-full max-w-3xl">
      <CardHeader>
        <CardTitle>New motor insurance claim</CardTitle>
        <CardDescription>
          Enter the claim details and attach the documents. Submitting registers the claim and gives you a claim number.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form key={resetKey} onSubmit={submit} className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <Label htmlFor="customerName">Customer name</Label>
              <Input id="customerName" required value={form.customerName} onChange={set('customerName')} />
            </div>
            <div className="space-y-1">
              <Label htmlFor="policyNumber">Policy number</Label>
              <Input id="policyNumber" required placeholder="POL-982341" value={form.policyNumber} onChange={set('policyNumber')} />
            </div>
            <div className="space-y-1">
              <Label htmlFor="vehicleRegistration">Vehicle registration</Label>
              <Input id="vehicleRegistration" required value={form.vehicleRegistration} onChange={set('vehicleRegistration')} />
            </div>
            <div className="space-y-1">
              <Label htmlFor="vehicleModel">Vehicle model</Label>
              <Input id="vehicleModel" value={form.vehicleModel} onChange={set('vehicleModel')} />
            </div>
            <div className="space-y-1">
              <Label htmlFor="incidentDate">Incident date</Label>
              <Input id="incidentDate" type="date" required value={form.incidentDate} onChange={set('incidentDate')} />
            </div>
            <div className="space-y-1">
              <Label htmlFor="claimAmount">Claim amount (INR)</Label>
              <Input id="claimAmount" type="number" min="0" step="0.01" required value={form.claimAmount} onChange={set('claimAmount')} />
            </div>
          </div>

          <div className="space-y-1">
            <Label htmlFor="incidentDescription">Incident description</Label>
            <Textarea id="incidentDescription" rows={3} value={form.incidentDescription} onChange={set('incidentDescription')} />
          </div>

          <div className="space-y-3">
            <h3 className="text-sm font-semibold">Documents (PDF)</h3>
            {DOCUMENT_SLOTS.map((s) => (
              <div key={s.key} className="grid items-center gap-2 sm:grid-cols-[1fr_1.4fr]">
                <Label htmlFor={`f-${s.key}`} className="break-words">
                  {s.label}
                  {s.required ? ' *' : ''}
                </Label>
                <div className="flex items-center gap-2">
                  <Input
                    key={`${s.key}-${resets[s.key] ?? 0}`}
                    id={`f-${s.key}`}
                    type="file"
                    accept="application/pdf,image/*"
                    onChange={(e) => {
                      const file = e.target.files?.[0]
                      setFiles((f) => {
                        const next = { ...f }
                        if (file) next[s.key] = file
                        else delete next[s.key]
                        return next
                      })
                    }}
                  />
                  {files[s.key] && (
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        setFiles((f) => {
                          const next = { ...f }
                          delete next[s.key]
                          return next
                        })
                        setResets((r) => ({ ...r, [s.key]: (r[s.key] ?? 0) + 1 }))
                      }}
                    >
                      Remove
                    </Button>
                  )}
                </div>
              </div>
            ))}
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
            {busy ? 'Submitting...' : 'Submit claim'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
