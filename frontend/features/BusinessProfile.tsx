'use client'

import { useEffect, useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import {
  BadgeCheck,
  Building2,
  CheckCircle2,
  FileCheck2,
  FileText,
  Loader2,
  LockKeyhole,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  UploadCloud,
  UserRound,
  XCircle,
} from 'lucide-react'
import {
  useAddDocumentToBusinessVault,
  useBusinessProfile,
  useBusinessProfileDocuments,
  useProjects,
  useRemoveDocumentFromBusinessVault,
  useUpdateBusinessProfile,
  useUploadDocument,
  useVerifyBusinessProfile,
} from '@/hooks/useApi'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

const EMPTY_FORM = {
  company_name: '',
  business_type: '',
  industry: '',
  sector: '',
  pan: '',
  gstin: '',
  udyam_number: '',
  registered_address: '',
  registered_state: '',
  registered_district: '',
  registered_city: '',
  registered_pincode: '',
}

type ProfileForm = typeof EMPTY_FORM

function verificationLabel(status?: string) {
  switch (status) {
    case 'PROTOTYPE_VERIFIED':
      return { text: 'Prototype verified', variant: 'success' as const, icon: CheckCircle2 }
    case 'PROTOTYPE_REJECTED':
      return { text: 'Prototype rejected', variant: 'danger' as const, icon: XCircle }
    case 'FORMAT_VALIDATED':
      return { text: 'Format validated', variant: 'info' as const, icon: BadgeCheck }
    case 'FORMAT_INVALID':
      return { text: 'Invalid format', variant: 'danger' as const, icon: XCircle }
    default:
      return { text: 'Not verified', variant: 'outline' as const, icon: ShieldCheck }
  }
}

function documentStatusVariant(status: string): 'success' | 'warning' | 'danger' | 'info' | 'outline' | 'default' {
  switch (status) {
    case 'VERIFIED':
      return 'success'
    case 'WARNING':
    case 'PROCESSING':
      return 'warning'
    case 'REJECTED':
    case 'EXPIRED':
      return 'danger'
    case 'UPLOADED':
      return 'info'
    default:
      return 'outline'
  }
}

export function BusinessProfile() {
  const queryClient = useQueryClient()
  const { data: profile, isLoading: profileLoading, isError: profileError } = useBusinessProfile()
  const { data: vaultData, isLoading: vaultLoading } = useBusinessProfileDocuments()
  const { data: projects } = useProjects()
  const updateProfile = useUpdateBusinessProfile()
  const verifyProfile = useVerifyBusinessProfile()
  const addToVault = useAddDocumentToBusinessVault()
  const removeFromVault = useRemoveDocumentFromBusinessVault()
  const uploadDocument = useUploadDocument()

  const [form, setForm] = useState<ProfileForm>(EMPTY_FORM)
  const [saved, setSaved] = useState(false)
  const [message, setMessage] = useState('')
  const [selectedProject, setSelectedProject] = useState('')
  const [uploadError, setUploadError] = useState('')

  useEffect(() => {
    if (!profile) return
    setForm({
      company_name: profile.company_name || '',
      business_type: profile.business_type || '',
      industry: profile.industry || '',
      sector: profile.sector || '',
      pan: profile.pan || '',
      gstin: profile.gstin || '',
      udyam_number: profile.udyam_number || '',
      registered_address: profile.registered_address || '',
      registered_state: profile.registered_state || '',
      registered_district: profile.registered_district || '',
      registered_city: profile.registered_city || '',
      registered_pincode: profile.registered_pincode || '',
    })
  }, [profile])

  const documents: any[] = Array.isArray(vaultData?.documents) ? vaultData.documents : []
  const vaultDocuments = useMemo(() => documents.filter((doc) => doc.in_vault), [documents])
  const availableDocuments = useMemo(() => documents.filter((doc) => !doc.in_vault), [documents])

  if (profileLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-gray-600">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <p className="mt-4 text-sm">Loading business profile...</p>
      </div>
    )
  }

  if (profileError || !profile) {
    return (
      <Card>
        <CardContent className="py-16 text-center">
          <p className="text-lg font-semibold text-gray-900">Business profile unavailable</p>
          <p className="mt-2 text-sm text-gray-600">
            Please refresh and try again. Your existing projects are not affected.
          </p>
        </CardContent>
      </Card>
    )
  }

  const updateField = (field: keyof ProfileForm, value: string) => {
    setSaved(false)
    setMessage('')
    setForm((current) => ({ ...current, [field]: value }))
  }

  const handleSave = async () => {
    setMessage('')
    try {
      await updateProfile.mutateAsync(form)
      setSaved(true)
      setMessage('Business profile saved successfully.')
      queryClient.invalidateQueries({ queryKey: ['business-profile'] })
    } catch (error: any) {
      setSaved(false)
      setMessage(error?.response?.data?.detail || 'Could not save your business profile.')
    }
  }

  const handleVerify = async () => {
    setMessage('')
    try {
      await verifyProfile.mutateAsync()
      setMessage('Prototype verification completed. Results are clearly marked below.')
      queryClient.invalidateQueries({ queryKey: ['business-profile'] })
    } catch (error: any) {
      setMessage(error?.response?.data?.detail || 'Prototype verification could not be completed.')
    }
  }

  const handleAddToVault = async (documentId: string) => {
    try {
      await addToVault.mutateAsync(documentId)
      queryClient.invalidateQueries({ queryKey: ['business-profile-documents'] })
      setMessage('Document added to the reusable Data Vault.')
    } catch (error: any) {
      setMessage(error?.response?.data?.detail || 'Could not add the document to the vault.')
    }
  }

  const handleRemoveFromVault = async (documentId: string) => {
    try {
      await removeFromVault.mutateAsync(documentId)
      queryClient.invalidateQueries({ queryKey: ['business-profile-documents'] })
      setMessage('Document removed from the reusable Data Vault.')
    } catch (error: any) {
      setMessage(error?.response?.data?.detail || 'Could not remove the document from the vault.')
    }
  }

  const handleUpload = async (file: File) => {
    if (!selectedProject) {
      setUploadError('Select a project before uploading a document.')
      return
    }
    setUploadError('')
    try {
      const document = await uploadDocument.mutateAsync({ projectId: selectedProject, file })
      await addToVault.mutateAsync(document.id)
      queryClient.invalidateQueries({ queryKey: ['business-profile-documents'] })
      setMessage(`${file.name} was uploaded and added to your reusable Data Vault.`)
    } catch (error: any) {
      setUploadError(error?.response?.data?.detail || 'Upload failed. Please try again.')
    }
  }

  const score = profile.completeness?.score ?? 0
  const missingFields: string[] = profile.completeness?.missing_fields ?? []
  const identityPresent = profile.completeness?.identity_fields_present ?? 0
  const identityTotal = profile.completeness?.identity_fields_total ?? 3
  const projectList: any[] = Array.isArray(projects) ? projects : []

  const identityItems = [
    { key: 'pan', label: 'PAN', value: profile.pan, status: profile.verification_status?.pan },
    { key: 'gstin', label: 'GSTIN', value: profile.gstin, status: profile.verification_status?.gstin },
    {
      key: 'udyam_number',
      label: 'Udyam',
      value: profile.udyam_number,
      status: profile.verification_status?.udyam_number,
    },
  ]

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-blue-700 font-medium">
            <UserRound className="w-4 h-4" />
            Entrepreneur Profile
          </div>
          <h1 className="mt-1 text-3xl font-bold text-gray-900">Business Profile & Data Vault</h1>
          <p className="mt-2 max-w-3xl text-gray-600">
            Enter core business information once and reuse it across future approval and compliance
            journeys.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={handleVerify}
            disabled={verifyProfile.isPending}
          >
            {verifyProfile.isPending ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4 mr-2" />
            )}
            Run Prototype Verification
          </Button>
          <Button onClick={handleSave} disabled={updateProfile.isPending}>
            {updateProfile.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            Save Profile
          </Button>
        </div>
      </div>

      <div className="rounded-xl border border-blue-200 bg-blue-50 p-5">
        <div className="flex gap-3">
          <LockKeyhole className="mt-0.5 h-5 w-5 flex-none text-blue-700" />
          <div>
            <p className="font-semibold text-blue-900">Your reusable data stays owner-scoped</p>
            <p className="mt-1 text-sm text-blue-800">
              The profile and vault use your existing authenticated account. Prototype verification
              uses the project's local simulator only; no live government API is called.
            </p>
          </div>
        </div>
      </div>

      {message && (
        <div
          className={`rounded-lg border px-4 py-3 text-sm ${
            saved
              ? 'border-green-200 bg-green-50 text-green-800'
              : 'border-blue-200 bg-blue-50 text-blue-800'
          }`}
        >
          {message}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[1.45fr_0.85fr] gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Business identity</CardTitle>
            <CardDescription>
              This information becomes the reusable foundation for future applications.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label className="text-sm font-medium text-gray-700">
                Company name
                <Input value={form.company_name} onChange={(e) => updateField('company_name', e.target.value)} placeholder="ABC Textiles Pvt Ltd" />
              </label>
              <label className="text-sm font-medium text-gray-700">
                Business type
                <Input value={form.business_type} onChange={(e) => updateField('business_type', e.target.value)} placeholder="Manufacturing" />
              </label>
              <label className="text-sm font-medium text-gray-700">
                Industry
                <Input value={form.industry} onChange={(e) => updateField('industry', e.target.value)} placeholder="Textile" />
              </label>
              <label className="text-sm font-medium text-gray-700">
                Sector
                <Input value={form.sector} onChange={(e) => updateField('sector', e.target.value)} placeholder="Textile processing" />
              </label>
            </section>

            <div className="border-t border-gray-200 pt-6">
              <div className="mb-4 flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-blue-600" />
                <div>
                  <h3 className="font-semibold text-gray-900">Identity references</h3>
                  <p className="text-xs text-gray-500">
                    Format checks are local; prototype verification is simulated.
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <label className="text-sm font-medium text-gray-700">
                  PAN
                  <Input
                    value={form.pan}
                    onChange={(e) => updateField('pan', e.target.value.toUpperCase())}
                    placeholder="ABCDE1234F"
                    maxLength={10}
                  />
                </label>
                <label className="text-sm font-medium text-gray-700">
                  GSTIN
                  <Input
                    value={form.gstin}
                    onChange={(e) => updateField('gstin', e.target.value.toUpperCase())}
                    placeholder="27ABCDE1234F1Z5"
                    maxLength={15}
                  />
                </label>
                <label className="text-sm font-medium text-gray-700">
                  Udyam number
                  <Input
                    value={form.udyam_number}
                    onChange={(e) => updateField('udyam_number', e.target.value.toUpperCase())}
                    placeholder="UDYAM-MH-18-0001234"
                  />
                </label>
              </div>

              <div className="mt-5 grid grid-cols-1 gap-3">
                {identityItems.map((item) => {
                  const verification = verificationLabel(item.status?.status)
                  const Icon = verification.icon
                  return (
                    <div
                      key={item.key}
                      className="flex flex-col gap-2 rounded-lg border border-gray-200 bg-gray-50 p-3 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div>
                        <p className="text-sm font-semibold text-gray-900">{item.label}</p>
                        <p className="text-xs text-gray-500">{item.value || 'Not provided'}</p>
                      </div>
                      <Badge variant={verification.variant}>
                        <Icon className="mr-1 h-3.5 w-3.5" />
                        {verification.text}
                      </Badge>
                    </div>
                  )
                })}
              </div>
            </div>

            <div className="border-t border-gray-200 pt-6">
              <h3 className="font-semibold text-gray-900">Registered address</h3>
              <div className="mt-4 space-y-4">
                <label className="block text-sm font-medium text-gray-700">
                  Address
                  <textarea
                    value={form.registered_address}
                    onChange={(e) => updateField('registered_address', e.target.value)}
                    rows={3}
                    placeholder="Registered office address"
                    className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-gray-900 placeholder:text-gray-400 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </label>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <label className="text-sm font-medium text-gray-700">
                    State
                    <Input value={form.registered_state} onChange={(e) => updateField('registered_state', e.target.value)} placeholder="Maharashtra" />
                  </label>
                  <label className="text-sm font-medium text-gray-700">
                    District
                    <Input value={form.registered_district} onChange={(e) => updateField('registered_district', e.target.value)} placeholder="Nashik" />
                  </label>
                  <label className="text-sm font-medium text-gray-700">
                    City
                    <Input value={form.registered_city} onChange={(e) => updateField('registered_city', e.target.value)} placeholder="Nashik" />
                  </label>
                  <label className="text-sm font-medium text-gray-700">
                    PIN code
                    <Input value={form.registered_pincode} onChange={(e) => updateField('registered_pincode', e.target.value)} placeholder="422007" maxLength={10} />
                  </label>
                </div>
              </div>
            </div>

            {missingFields.length > 0 && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                <p className="text-sm font-semibold text-amber-900">Complete your profile</p>
                <p className="mt-1 text-sm text-amber-800">
                  Missing: {missingFields.join(', ')}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Profile readiness</CardTitle>
              <CardDescription>Core information coverage for future applications.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <div className="relative h-20 w-20 rounded-full border-8 border-blue-100 flex items-center justify-center">
                  <span className="text-xl font-bold text-blue-700">{score}%</span>
                </div>
                <div className="min-w-0">
                  <p className="font-semibold text-gray-900">
                    {profile.completeness?.completed_fields ?? 0} of {profile.completeness?.total_fields ?? 0} core fields complete
                  </p>
                  <p className="mt-1 text-sm text-gray-600">
                    Identity references: {identityPresent}/{identityTotal}
                  </p>
                </div>
              </div>
              <div className="mt-5 h-2 rounded-full bg-gray-100 overflow-hidden">
                <div
                  className="h-full rounded-full bg-blue-600 transition-all"
                  style={{ width: `${score}%` }}
                />
              </div>
              <div className="mt-5 rounded-lg bg-gray-50 p-3 text-xs text-gray-600">
                <p className="font-semibold text-gray-800">What this unlocks</p>
                <p className="mt-1">
                  Future approval forms can consume this stable profile without asking you to repeat
                  the same business information.
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Reusable document vault</CardTitle>
              <CardDescription>
                Existing project documents can be promoted into this vault for reuse.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-4">
                <div className="flex items-center gap-2">
                  <UploadCloud className="h-5 w-5 text-blue-600" />
                  <p className="text-sm font-semibold text-gray-900">Upload a reusable document</p>
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  Documents still belong to their source project; the vault creates a reusable
                  business-level link.
                </p>
                <Select
                  value={selectedProject}
                  onChange={(e) => setSelectedProject(e.target.value)}
                  className="mt-3"
                >
                  <option value="">Select source project...</option>
                  {projectList.map((project: any) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </Select>
                <label className="mt-3 inline-flex w-full cursor-pointer items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50">
                  {uploadDocument.isPending || addToVault.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Plus className="h-4 w-4" />
                  )}
                  Choose file
                  <input
                    type="file"
                    className="hidden"
                    accept=".pdf,.png,.jpg,.jpeg,.doc,.docx"
                    disabled={uploadDocument.isPending || addToVault.isPending}
                    onChange={(e) => {
                      const file = e.target.files?.[0]
                      if (file) void handleUpload(file)
                      e.currentTarget.value = ''
                    }}
                  />
                </label>
                {uploadError && <p className="mt-2 text-xs text-red-600">{uploadError}</p>}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>Vault documents</CardTitle>
            <CardDescription>
              {vaultDocuments.length} reusable document{vaultDocuments.length === 1 ? '' : 's'} ready for future application workflows.
            </CardDescription>
          </div>
          <Badge variant="outline">
            <FileCheck2 className="mr-1 h-3.5 w-3.5" />
            {vaultData?.summary?.in_vault ?? 0} in vault
          </Badge>
        </CardHeader>
        <CardContent>
          {vaultLoading ? (
            <div className="py-10 text-center text-sm text-gray-500">Loading document vault...</div>
          ) : vaultDocuments.length === 0 ? (
            <div className="rounded-lg border border-dashed border-gray-300 py-12 text-center">
              <FileText className="mx-auto h-8 w-8 text-gray-300" />
              <p className="mt-3 text-sm font-medium text-gray-900">No reusable documents yet</p>
              <p className="mt-1 text-sm text-gray-500">
                Upload a document above or promote an existing project document below.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {vaultDocuments.map((doc) => (
                <div key={doc.id} className="rounded-lg border border-gray-200 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate font-medium text-gray-900">{doc.file_name}</p>
                      <p className="mt-1 text-xs text-gray-500">
                        {doc.document_type || 'General document'}
                      </p>
                    </div>
                    <Badge variant={documentStatusVariant(doc.status)}>{doc.status}</Badge>
                  </div>
                  <div className="mt-4 text-xs text-gray-500">
                    Source project: <span className="font-medium text-gray-700">{doc.project_name}</span>
                  </div>
                  {doc.validation_errors?.length > 0 && (
                    <p className="mt-2 text-xs text-amber-700">
                      {doc.validation_errors.length} validation warning{doc.validation_errors.length === 1 ? '' : 's'}
                    </p>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-4 w-full"
                    onClick={() => void handleRemoveFromVault(doc.id)}
                    disabled={removeFromVault.isPending}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Remove from Vault
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Documents available to add</CardTitle>
          <CardDescription>
            These are your existing project documents that are not yet in the reusable business vault.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {availableDocuments.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-500">
              All existing documents are already in your Data Vault.
            </p>
          ) : (
            <div className="divide-y divide-gray-200">
              {availableDocuments.map((doc) => (
                <div key={doc.id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="rounded-lg bg-blue-50 p-2">
                      <FileText className="h-4 w-4 text-blue-600" />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate font-medium text-gray-900">{doc.file_name}</p>
                      <p className="text-xs text-gray-500">
                        {doc.document_type || 'General document'} · {doc.project_name}
                      </p>
                    </div>
                    <Badge variant={documentStatusVariant(doc.status)}>{doc.status}</Badge>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="shrink-0"
                    onClick={() => void handleAddToVault(doc.id)}
                    disabled={addToVault.isPending}
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    Add to Vault
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex items-start gap-3 rounded-lg border border-gray-200 bg-white p-4 text-xs text-gray-500">
        <Building2 className="mt-0.5 h-4 w-4 flex-none text-gray-400" />
        <p>
          The Data Vault does not move or duplicate your source documents. It creates a reusable
          business-level association around the existing project document record, so future approval
          flows can reference the same verified file.
        </p>
      </div>
    </div>
  )
}

export default BusinessProfile
